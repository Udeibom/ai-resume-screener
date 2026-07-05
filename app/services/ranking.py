import json
import os
from typing import Any, Dict, List

import mlflow
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.services.ai_service import AIService

# Set the target MLflow tracking URI (points to our new Docker container service)
mlflow.set_tracking_uri(
    os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
)
mlflow.set_experiment("Resume_Screening_Rankings")


class CandidateRankingEngine:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.ai = AIService()

    async def rank_candidates(
        self,
        job_description: str,
        limit_candidates: int = 5,
    ) -> List[Dict[str, Any]]:
        logger.info(
            "Initiating candidate matching sequence",
            extra_context={"limit": limit_candidates},
        )

        job_vector = (
            await self.ai.generate_embeddings(
                [job_description]
            )
        )[0]

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
            logger.info("No vectors returned from semantic lookup.")
            return []

        candidates_context: Dict[int, Dict[str, Any]] = {}

        for row in rows:
            res_id = row.resume_id

            if res_id not in candidates_context:
                candidates_context[res_id] = {
                    "filename": row.filename,
                    "profile": row.parsed_profile,
                    "matched_snippets": [],
                }

            if (
                row.chunk_text
                not in candidates_context[res_id]["matched_snippets"]
            ):
                candidates_context[res_id]["matched_snippets"].append(
                    row.chunk_text
                )

        system_prompt = (
            "You are an executive technical recruiter. "
            "Analyze the candidate's resume context "
            "against the job description. "
            "Provide a JSON response containing exactly two fields:\n"
            "1. 'fit_score': An integer rating from 0 to 100.\n"
            "2. 'justification': A concise sentence explaining "
            "the score based purely on verified skills."
        )

        ranked_results: List[Dict[str, Any]] = []

        # Start an MLflow tracking run to evaluate this operational batch execution
        with mlflow.start_run(run_name="batch_llm_grading"):
            # Log hyperparameters/configurations
            mlflow.log_param("llm_model", self.ai.llm_model)
            mlflow.log_param("embedding_model", self.ai.embedding_model)
            mlflow.log_text(
                system_prompt,
                "prompts/system_prompt.txt",
            )
            mlflow.log_text(
                job_description,
                "inputs/job_description.txt",
            )

            for res_id, data in list(candidates_context.items())[
                :limit_candidates
            ]:
                user_content = (
                    f"JOB DESCRIPTION:\n{job_description}\n\n"
                    f"CANDIDATE PROFILE:\n"
                    f"{json.dumps(data['profile'])}\n\n"
                    "RELEVANT RESUME SNIPPETS:\n"
                    + "\n---\n".join(data["matched_snippets"])
                )

                try:
                    response = (
                        await self.ai.client.chat.completions.create(
                            model=self.ai.llm_model,
                            response_format={
                                "type": "json_object"
                            },
                            messages=[
                                {
                                    "role": "system",
                                    "content": system_prompt,
                                },
                                {
                                    "role": "user",
                                    "content": user_content,
                                },
                            ],
                        )
                    )

                    evaluation = json.loads(
                        response.choices[0].message.content
                    )

                    fit_score = evaluation.get(
                        "fit_score",
                        0,
                    )

                    # Log metrics per profile directly inside the MLflow execution loop
                    mlflow.log_metric(
                        f"candidate_{res_id}_fit_score",
                        fit_score,
                    )

                    ranked_results.append(
                        {
                            "candidate_id": res_id,
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
                        "Successfully evaluated candidate score",
                        extra_context={
                            "candidate_id": res_id,
                            "score": fit_score,
                        },
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to grade candidate context structural loop: {str(e)}",
                        exc_info=True,
                    )
                    continue

        return sorted(
            ranked_results,
            key=lambda x: x["fit_score"],
            reverse=True,
        )