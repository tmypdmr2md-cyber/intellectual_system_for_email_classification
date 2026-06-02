import logging
from typing import Optional

from src.core import config

logger = logging.getLogger(__name__)


class DecisionEngine:
    def decide(
        self,
        rule_result: dict,
        similar_emails: list = None,
        llm_result: dict = None,
    ) -> dict:
        logger.info("DecisionEngine started")
        logger.debug("rule_result=%s", rule_result)
        logger.debug("similar_emails=%s", similar_emails)
        logger.debug("llm_result=%s", llm_result)

        pre_llm_decision = self.decide_pre_llm(
            rule_result=rule_result,
            similar_emails=similar_emails,
        )
        # пробуем запустить пайп лайн принятия решения до LLM, чтобы не нагружать LLM лишними запросами по апихе, если мы уже можем принять решение на более ранних этапах
        if pre_llm_decision:
            return pre_llm_decision
        # если не получилось принять решение до LLM, то смотрим на результат LLM, который может помочь 
        # нам принять решение, а может и не помочь, в зависимости от того насколько он уверен в себе, А ГИГАЧАДДД ВСЕГДА УВЕРЕН В СЕБЕ 
        if llm_result:
            logger.info(
                "Decision made by LLM fallback: category=%s confidence=%s method=%s",
                llm_result.get("category"),
                llm_result.get("confidence"),
                llm_result.get("method"),
            )

            return {
                "category": llm_result.get("category", "unknown"),
                "confidence": llm_result.get("confidence", 0.0),
                "method": llm_result.get("method", "llm"),
                "reason": llm_result.get("reason", "LLM fallback decision"),
                "is_new_category": llm_result.get("is_new_category", False),
                "new_category_title": llm_result.get("new_category_title"),
                "new_category_description": llm_result.get("new_category_description"),
                "corrected_subject": llm_result.get("corrected_subject"),
                "corrected_body": llm_result.get("corrected_body"),
                "grammar_issues_found": llm_result.get("grammar_issues_found", False),
                "grammar_corrections": llm_result.get("grammar_corrections", []),
            }

        rule_category = rule_result.get("category", "unknown")
        rule_confidence = rule_result.get("confidence", 0.0)

        logger.warning(
            "No confident decision. rule_category=%s rule_confidence=%s has_similar=%s has_llm=%s",
            rule_category,
            rule_confidence,
            bool(similar_emails),
            bool(llm_result),
        )

        return {
            "category": "unknown",
            "confidence": 0.0,
            "method": "decision_engine",
            "reason": "No confident decision",
        }

    def decide_pre_llm(
        self,
        rule_result: dict,
        similar_emails: list = None,
    ) -> Optional[dict]:
        rule_decision = self._rule_decision(rule_result)
        if rule_decision:
            return rule_decision

        return self._semantic_decision(similar_emails or [])

    def _rule_decision(self, rule_result: dict) -> Optional[dict]:
        rule_category = rule_result.get("category", "unknown")
        rule_confidence = rule_result.get("confidence", 0.0)

        if (
            rule_category == "unknown"
            or rule_confidence < config.RULE_CONFIDENCE_THRESHOLD
        ):
            return None

        logger.info(
            "Decision made by rule_based: category=%s confidence=%s",
            rule_category,
            rule_confidence,
        )

        return {
            "category": rule_category,
            "confidence": rule_confidence,
            "method": "rule_based",
            "reason": rule_result.get("reason", "Rule based decision"),
        }

    def _semantic_decision(self, similar_emails: list) -> Optional[dict]:
        strong_similar = self._get_strong_similar(similar_emails)
        if not strong_similar:
            return None

        category_from_semantic = strong_similar.get("category")

        if category_from_semantic and category_from_semantic != "unknown":
            logger.info(
                "Decision made by semantic_search: category=%s similarity=%s",
                category_from_semantic,
                strong_similar.get("similarity"),
            )

            return {
                "category": category_from_semantic,
                "confidence": strong_similar.get("similarity", 0.0),
                "method": "semantic_search",
                "reason": f"Found similar email with category {category_from_semantic} and similarity {strong_similar.get('similarity')}",
            }

        logger.warning(
            "Strong similar email was found, but it has no category. email_id=%s similarity=%s",
            strong_similar.get("email_id"),
            strong_similar.get("similarity"),
        )

        return None

    def _get_strong_similar(self, similar_emails: list) -> Optional[dict]:
        if not similar_emails:
            logger.info("No similar emails found")
            return None

        best = similar_emails[0]
        best_similarity = best.get("similarity", 0.0)

        logger.info(
            "Best similar email found: email_id=%s similarity=%s category=%s",
            best.get("email_id"),
            best_similarity,
            best.get("category"),
        )

        for item in similar_emails:
            similarity = item.get("similarity", 0.0)
            if similarity < config.SEMANTIC_SIMILARITY_THRESHOLD:
                break

            category = item.get("category")
            if category and category != "unknown":
                return item

        return None
