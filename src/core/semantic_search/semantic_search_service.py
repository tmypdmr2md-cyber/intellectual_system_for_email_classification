import math


# Semantic Search отвечает за поиск наиболее похожих писем
# на основе векторных представлений (embeddings) которые сы уже сделали
# Используется как дополнительный источник информации для классификации 
class SemanticSearchService:
    # Косинусное сходство показывает, насколько два письма похожи по смыслу
    # Чем ближе результат к 1.0, тем более похожими считаются embeddings
    def cosine_similarity(self, vector_a: list, vector_b: list) -> float:
        if len(vector_a) != len(vector_b):
            return 0.0

        # Вычисляем длину каждого вектора
        # Нужна для нормализации при расчёте cosine similarity
        norm_a = math.sqrt(sum(value * value for value in vector_a))
        norm_b = math.sqrt(sum(value * value for value in vector_b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        # Скалярное произведение показывает направление и близость векторов
        dot_product = sum(a * b for a, b in zip(vector_a, vector_b))

        return float(dot_product / (norm_a * norm_b))

    # Сравнивает embedding текущего письма со всеми ранее сохранёнными письмами
    # На выходе возвращает список самых похожих писем с их категориями
    def find_similar(
        self,
        current_embedding: list,
        stored_embeddings: list,
        limit: int = 5,
    ) -> list:
        results = []

        # Последовательно сравниваем текущее письмо со всей историей писем
        # фича в том что чем больше писем в истории, тем выше шанс найти действительно похожее письмо и обработать его 
        # категорию в разы быстрее, поэтому данное архитектурное решение идеально подходит для нашей задачи, 
        # так как мы не ограничены количеством писем в истории и можем позволить себе сравнивать
        #  с большим количеством писем, чтобы найти максимально релевантные совпадения без постоянного вызова LLM 
        # и обучения каких-то ллм моделей на нашей специфической задаче, что может быть сложно и дорого
        for item in stored_embeddings:
            embedding = item.get("embedding") if isinstance(item, dict) else item.embedding
            email_id = item.get("email_id") if isinstance(item, dict) else item.email_id
            category = item.get("category") if isinstance(item, dict) else getattr(item, "category", None)

            similarity = self.cosine_similarity(
                current_embedding,
                embedding,
            )

            # Сохраняем результат сравнения для последующей сортировки
            results.append(
                {
                    "email_id": email_id,
                    "similarity": similarity,
                    "category": category,
                }
            )

        # Сортируем письма по убыванию похожести,
        # чтобы в начале списка были самые релевантные совпадения
        results.sort(
            key=lambda item: item["similarity"],
            reverse=True,
        )

        # Возвращаем только топ наиболее похожих писем
        return results[:limit]
