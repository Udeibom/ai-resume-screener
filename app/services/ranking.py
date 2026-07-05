import json
import os
from typing import Any, Dict, List

import mlflow
from google.genai import types
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.services.ai_service import AIService


class CandidateRankingEngine:
    """
    Production ranking engine.

    Features:
    - Lazy MLflow initialization
    - Gemini-powered evaluation
    - No side effects during import
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.ai = AIService()
        self._mlflow_initialized = False

    def _initialize_mlflow(self) -> None:
        """
        Initialize MLflow only when the ranking engine is actually used.
        """

        if self._mlflow_initialized:
            return

        tracking_uri = os.getenv(
            "MLFLOW_TRACKING_URI",
            "http://localhost:5000",
        )

        try:
            mlflow.set_tracking_uri(tracking_uri)
            mlflow.set_experiment("Resume_Screening_Rankings")
            self._mlflow_initialized = True

            logger.info(
                "MLflow initialized.",
                extra_context={"tracking_uri": tracking_uri},
            )

        except Exception as exc:
            logger.warning(
                f"MLflow unavailable. Continuing without experiment tracking. {exc}"
            )

    async def rank_candidates(
        self,
        job_description: str,
        limit_candidates: int = 5,
    ) -> List[Dict[str, Any]]:

        logger.info(
            "Initiating candidate ranking.",
            extra_context={"limit": limit_candidates},
        )

        self._initialize_mlflow()

        job_vector = (await self.ai.generate_embeddings([job_description]))[0]

        query = text(
            """
            SELECT
                rc.resume_id,
                r.filename,
                r.parsed_profile,
                rc.chunk_text,
                (rc.embedding <=> :vector) AS distance
            FROM resume_chunks rc
            JOIN resumes r
                ON rc.resume_id = r.id
            ORDER BY rc.embedding <=> :vector
            LIMIT 20;
            """
        )

        result = await self.db.execute(
            query,
            {"vector": str(job_vector)},
        )

        rows = result.fetchall()

        if not rows:
            logger.info("No matching candidates found.")
            return []

        candidates_context: Dict[int, Dict[str, Any]] = {}

        for row in rows:
            resume_id = row.resume_id

            if resume_id not in candidates_context:
                candidates_context[resume_id] = {
                    "filename": row.filename,
                    "profile": row.parsed_profile,
                    "matched_snippets": [],
                }

            if row.chunk_text not in candidates_context[resume_id]["matched_snippets"]:
                candidates_context[resume_id]["matched_snippets"].append(row.chunk_text)

        system_prompt = """
You are an expert technical recruiter.

Compare the candidate against the job description.

Return ONLY JSON.

Schema:

{
  "fit_score": integer,
  "justification": string
}

The score must be between 0 and 100.

Do not invent qualifications.
"""

        ranked_results = []

        mlflow_context = (
            mlflow.start_run(run_name="batch_llm_grading")
            if self._mlflow_initialized
            else None
        )

        if mlflow_context:
            mlflow_context.__enter__()

            mlflow.log_param("llm_model", self.ai.llm_model)
            mlflow.log_param("embedding_model", self.ai.embedding_model)
            mlflow.log_text(system_prompt, "prompts/system_prompt.txt")
            mlflow.log_text(job_description, "inputs/job_description.txt")

        try:

            for resume_id, data in list(candidates_context.items())[:limit_candidates]:

                prompt = f"""
JOB DESCRIPTION

{job_description}

CANDIDATE PROFILE

{json.dumps(data['profile'], indent=2)}

MATCHED RESUME SNIPPETS

{chr(10).join(data["matched_snippets"])}
"""

                try:

                    response = await self.ai._run_with_retry(
                        lambda: self.ai.client.models.generate_content(
                            model=self.ai.llm_model,
                            contents=f"{system_prompt}\n\n{prompt}",
                            config=types.GenerateContentConfig(
                                temperature=0,
                                response_mime_type="application/json",
                            ),
                        )
                    )

                    evaluation = json.loads(response.text)

                    fit_score = int(evaluation.get("fit_score", 0))

                    if self._mlflow_initialized:
                        mlflow.log_metric(
                            f"candidate_{resume_id}_fit_score",
                            fit_score,
                        )

                    ranked_results.append(
                        {
                            "candidate_id": resume_id,
                            "filename": data["filename"],
                            "name": data["profile"].get(
                                "full_name",
                                "Unknown",
                            ),
                            "fit_score": fit_score,
                            "justification": evaluation.get(
                                "justification",
                                "",
                            ),
                        }
                    )

                    logger.info(
                        "Candidate evaluated.",
                        extra_context={
                            "candidate": resume_id,
                            "score": fit_score,
                        },
                    )

                except Exception as exc:

                    logger.exception(f"Failed evaluating candidate {resume_id}: {exc}")

        finally:

            if mlflow_context:
                mlflow_context.__exit__(None, None, None)

        return sorted(
            ranked_results,
            key=lambda x: x["fit_score"],
            reverse=True,
        )
