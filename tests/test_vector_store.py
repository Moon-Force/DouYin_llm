import time
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

from backend.memory.vector_store import VectorMemory


def make_settings(signature="cloud_text_embedding_3_small", strict=False, decay_halflife_hours=0):
    return SimpleNamespace(
        embedding_signature=lambda: signature,
        embedding_strict=strict,
        semantic_memory_min_score=0.35,
        semantic_memory_query_limit=6,
        semantic_final_k=3,
        memory_decay_halflife_hours=decay_halflife_hours,
    )


class VectorMemoryTests(unittest.TestCase):
    def test_collection_names_only_create_viewer_memory_collection(self):
        fake_client = MagicMock()
        fake_client.get_or_create_collection.return_value = MagicMock()
        fake_embedding = MagicMock()

        with patch("backend.memory.vector_store.chromadb") as chromadb_mock:
            chromadb_mock.PersistentClient.return_value = fake_client
            store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)

        fake_client.get_or_create_collection.assert_called_once_with("viewer_memories_cloud_text_embedding_3_small")
        self.assertIsNone(store.collection)

    def test_final_rank_key_combines_semantic_and_business_scores(self):
        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=MagicMock())
        item = {
            "memory_id": "m1",
            "memory_text": "不太能吃辣",
            "score": 0.8,
            "metadata": {
                "confidence": 0.9,
                "interaction_value_score": 0.95,
                "evidence_score": 0.7,
                "stability_score": 0.85,
                "source_kind": "manual",
                "is_pinned": 1,
                "updated_at": 100,
                "recall_count": 2,
            },
        }

        rank_key = store._final_rank_key(item, query_text="鍚冭荆", decay_halflife_hours=0)

        self.assertIsInstance(rank_key[0], float)
        self.assertEqual(len(rank_key), 2)

    def test_business_rerank_score_uses_interaction_evidence_and_stability(self):
        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=MagicMock())
        item = {
            "memory_id": "m1",
            "memory_text": "不太能吃辣",
            "score": 0.8,
            "metadata": {
                "confidence": 0.9,
                "interaction_value_score": 0.95,
                "evidence_score": 0.7,
                "stability_score": 0.85,
                "source_kind": "manual",
                "is_pinned": 1,
                "updated_at": 100,
                "recall_count": 2,
            },
        }

        score = store._business_rerank_score(item, query_text="鍚冭荆")

        self.assertGreater(score, 0.0)

    def test_similar_memories_prefers_higher_confidence_when_scores_are_close(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()
        fake_collection.query.return_value = {
            "ids": [["m1", "m2"]],
            "documents": [["likes ramen", "likes noodles"]],
            "metadatas": [[
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.9,
                    "updated_at": 200,
                    "recall_count": 2,
                },
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.4,
                    "updated_at": 300,
                    "recall_count": 1,
                },
            ]],
            "distances": [[0.6, 0.59]],
        }

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        result = store.similar_memories("likes eating noodles", "room-1", "viewer-1", limit=2)

        self.assertEqual(result[0]["memory_id"], "m1")

    def test_similar_memories_does_not_leak_memories_between_different_viewers(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]

        store = VectorMemory("data/chroma", settings=make_settings(strict=False), embedding_service=fake_embedding)
        store.memory_collection = None
        store._memory_items = [
            {
                "id": "mem-viewer-1",
                "document": "喜欢拉面",
                "metadata": {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.9,
                    "updated_at": 200,
                    "recall_count": 1,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                },
            },
            {
                "id": "mem-viewer-2",
                "document": "喜欢火锅",
                "metadata": {
                    "room_id": "room-1",
                    "viewer_id": "viewer-2",
                    "memory_type": "preference",
                    "confidence": 0.95,
                    "updated_at": 210,
                    "recall_count": 1,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                },
            },
        ]

        result = store.similar_memories("火锅", "room-1", "viewer-1", limit=3)

        self.assertEqual(result, [])

    def test_similar_memories_does_not_leak_memories_between_different_rooms(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]

        store = VectorMemory("data/chroma", settings=make_settings(strict=False), embedding_service=fake_embedding)
        store.memory_collection = None
        store._memory_items = [
            {
                "id": "mem-room-1",
                "document": "喜欢拉面",
                "metadata": {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.9,
                    "updated_at": 200,
                    "recall_count": 1,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                },
            },
            {
                "id": "mem-room-2",
                "document": "喜欢火锅",
                "metadata": {
                    "room_id": "room-2",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.95,
                    "updated_at": 210,
                    "recall_count": 1,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                },
            },
        ]

        result = store.similar_memories("火锅", "room-1", "viewer-1", limit=3)

        self.assertEqual(result, [])

    def test_non_strict_mode_falls_back_to_token_matching_when_query_fails(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()
        fake_collection.query.side_effect = RuntimeError("chroma down")

        store = VectorMemory("data/chroma", settings=make_settings(strict=False), embedding_service=fake_embedding)
        store.memory_collection = fake_collection
        store._memory_items = [
            {
                "id": "m1",
                "document": "likes ramen",
                "metadata": {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.9,
                    "updated_at": 200,
                    "recall_count": 1,
                },
            }
        ]

        result = store.similar_memories("likes ramen", "room-1", "viewer-1", limit=1)

        self.assertEqual(result[0]["memory_id"], "m1")

    def test_strict_mode_raises_when_query_fails(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()
        fake_collection.query.side_effect = RuntimeError("chroma down")

        store = VectorMemory("data/chroma", settings=make_settings(strict=True), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        with self.assertRaisesRegex(RuntimeError, "strict mode"):
            store.similar_memories("likes ramen", "room-1", "viewer-1", limit=1)

    def test_strict_mode_marks_backend_not_ready_when_chroma_is_missing(self):
        with patch("backend.memory.vector_store.chromadb", None):
            store = VectorMemory("data/chroma", settings=make_settings(strict=True), embedding_service=MagicMock())

        self.assertFalse(store.semantic_backend_ready())
        self.assertIn("Chroma", store.semantic_backend_reason())

    def test_add_memory_includes_status_source_and_pin_metadata(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        memory = SimpleNamespace(
            memory_id="mem-1",
            room_id="room-1",
            viewer_id="viewer-1",
            source_event_id="evt-1",
            memory_text="鍠滄璞氶鎷夐潰",
            memory_type="preference",
            confidence=0.91,
            updated_at=123,
            recall_count=2,
            status="active",
            source_kind="manual",
            is_pinned=True,
            stability_score=0.9,
            interaction_value_score=0.85,
            clarity_score=0.8,
            evidence_score=0.5,
        )

        store.add_memory(memory)

        upsert_kwargs = fake_collection.upsert.call_args.kwargs
        self.assertEqual(upsert_kwargs["metadatas"][0]["status"], "active")
        self.assertEqual(upsert_kwargs["metadatas"][0]["source_kind"], "manual")
        self.assertEqual(upsert_kwargs["metadatas"][0]["is_pinned"], 1)
        self.assertEqual(upsert_kwargs["metadatas"][0]["interaction_value_score"], 0.85)
        self.assertEqual(upsert_kwargs["metadatas"][0]["evidence_score"], 0.5)

    def test_add_memory_indexes_recall_text_but_keeps_canonical_text_in_metadata(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        memory = SimpleNamespace(
            memory_id="mem-1",
            room_id="room-1",
            viewer_id="viewer-1",
            source_event_id="evt-1",
            memory_text="喜欢拉面",
            memory_recall_text="喜欢拉面；爱吃面条；豚骨拉面；食物偏好",
            memory_type="preference",
            confidence=0.91,
            updated_at=123,
            recall_count=2,
            status="active",
            source_kind="auto",
            is_pinned=False,
        )

        store.add_memory(memory)

        upsert_kwargs = fake_collection.upsert.call_args.kwargs
        self.assertEqual(upsert_kwargs["documents"], ["喜欢拉面；爱吃面条；豚骨拉面；食物偏好"])
        fake_embedding.embed_text.assert_called_with("喜欢拉面；爱吃面条；豚骨拉面；食物偏好")
        self.assertEqual(upsert_kwargs["metadatas"][0]["memory_text"], "喜欢拉面")
        self.assertEqual(upsert_kwargs["metadatas"][0]["memory_recall_text"], "喜欢拉面；爱吃面条；豚骨拉面；食物偏好")

    def test_similar_memories_returns_canonical_text_when_document_is_recall_text(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()
        fake_collection.query.return_value = {
            "ids": [["mem-1"]],
            "documents": [["喜欢拉面；爱吃面条；豚骨拉面；食物偏好"]],
            "metadatas": [[
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "memory_text": "喜欢拉面",
                    "memory_recall_text": "喜欢拉面；爱吃面条；豚骨拉面；食物偏好",
                    "confidence": 0.9,
                    "updated_at": 200,
                    "recall_count": 2,
                    "status": "active",
                }
            ]],
            "distances": [[0.2]],
        }

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        result = store.similar_memories("最近想吃面", "room-1", "viewer-1", limit=1)

        self.assertEqual(result[0]["memory_text"], "喜欢拉面")
        self.assertEqual(result[0]["memory_recall_text"], "喜欢拉面；爱吃面条；豚骨拉面；食物偏好")

    def test_sync_memory_removes_deleted_or_invalid_entries(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.memory_collection = fake_collection
        store._memory_items = [
            {
                "id": "mem-1",
                "document": "鍠滄鎷夐潰",
                "metadata": {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                    "confidence": 0.8,
                    "updated_at": 10,
                    "recall_count": 1,
                },
            }
        ]

        store.sync_memory(
            SimpleNamespace(
                memory_id="mem-1",
                room_id="room-1",
                viewer_id="viewer-1",
                source_event_id="evt-1",
                memory_text="鍠滄鎷夐潰",
                memory_type="preference",
                confidence=0.8,
                updated_at=20,
                recall_count=1,
                status="deleted",
                source_kind="auto",
                is_pinned=False,
            )
        )

        self.assertEqual(store._memory_items, [])
        fake_collection.delete.assert_called_once_with(ids=["mem-1"])

    def test_similar_memories_filters_invalid_superseded_entries(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()
        fake_collection.query.return_value = {
            "ids": [["m-old", "m-new"]],
            "documents": [["likes spicy food", "cannot eat spicy food"]],
            "metadatas": [[
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.9,
                    "updated_at": 100,
                    "recall_count": 2,
                    "status": "invalid",
                    "source_kind": "auto",
                    "is_pinned": 0,
                    "superseded_by": "m-new",
                },
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.9,
                    "updated_at": 110,
                    "recall_count": 1,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                    "superseded_by": "",
                },
            ]],
            "distances": [[0.2, 0.25]],
        }

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        result = store.similar_memories("cannot eat spicy food", "room-1", "viewer-1", limit=2)

        self.assertEqual([item["memory_id"] for item in result], ["m-new"])

    def test_similar_memories_prefers_manual_and_pinned_when_scores_are_close(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()
        fake_collection.query.return_value = {
            "ids": [["m-auto", "m-manual"]],
            "documents": [["鍠滄鎷夐潰", "鍠滄鎷夐潰"]],
            "metadatas": [[
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.8,
                    "updated_at": 100,
                    "recall_count": 2,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                },
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.8,
                    "updated_at": 90,
                    "recall_count": 2,
                    "status": "active",
                    "source_kind": "manual",
                    "is_pinned": 1,
                },
            ]],
            "distances": [[0.4, 0.4]],
        }

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        result = store.similar_memories("鍠滄鎷夐潰", "room-1", "viewer-1", limit=2)

        self.assertEqual(result[0]["memory_id"], "m-manual")


    def test_prime_memory_index_warms_cache_without_reembedding_when_collection_count_matches(self):
        fake_embedding = MagicMock()
        fake_collection = MagicMock()
        fake_collection.count.return_value = 2
        fake_collection.get.return_value = {
            "ids": ["mem-1", "mem-2"],
            "documents": ["likes ramen", "likes noodles"],
            "metadatas": [
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "source_event_id": "evt-1",
                    "memory_text": "likes ramen",
                    "memory_recall_text": "likes ramen",
                    "confidence": 0.8,
                    "updated_at": 10,
                    "recall_count": 1,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                    "stability_score": 0.0,
                    "interaction_value_score": 0.0,
                    "clarity_score": 0.0,
                    "evidence_score": 0.0,
                    "expires_at": 0,
                },
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-2",
                    "memory_type": "preference",
                    "source_event_id": "evt-2",
                    "memory_text": "likes noodles",
                    "memory_recall_text": "likes noodles",
                    "confidence": 0.9,
                    "updated_at": 20,
                    "recall_count": 2,
                    "status": "active",
                    "source_kind": "manual",
                    "is_pinned": 1,
                    "stability_score": 0.0,
                    "interaction_value_score": 0.0,
                    "clarity_score": 0.0,
                    "evidence_score": 0.0,
                    "expires_at": 0,
                },
            ],
        }

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        memories = [
            SimpleNamespace(
                memory_id="mem-1",
                room_id="room-1",
                viewer_id="viewer-1",
                source_event_id="evt-1",
                memory_text="likes ramen",
                memory_type="preference",
                confidence=0.8,
                updated_at=10,
                recall_count=1,
                status="active",
                source_kind="auto",
                is_pinned=False,
                stability_score=0.0,
                interaction_value_score=0.0,
                clarity_score=0.0,
                evidence_score=0.0,
                expires_at=0,
            ),
            SimpleNamespace(
                memory_id="mem-2",
                room_id="room-1",
                viewer_id="viewer-2",
                source_event_id="evt-2",
                memory_text="likes noodles",
                memory_type="preference",
                confidence=0.9,
                updated_at=20,
                recall_count=2,
                status="active",
                source_kind="manual",
                is_pinned=True,
                stability_score=0.0,
                interaction_value_score=0.0,
                clarity_score=0.0,
                evidence_score=0.0,
                expires_at=0,
            ),
        ]

        store.prime_memory_index(memories)

        self.assertEqual([item["id"] for item in store._memory_items], ["mem-1", "mem-2"])
        fake_embedding.embed_text.assert_not_called()
        fake_embedding.embed_texts.assert_not_called()
        fake_collection.upsert.assert_not_called()

    def test_prime_memory_index_rebuilds_collection_when_collection_is_empty(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_texts.return_value = [[0.1, 0.2], [0.3, 0.4]]
        fake_collection = MagicMock()
        fake_collection.count.return_value = 0

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        memories = [
            SimpleNamespace(
                memory_id="mem-1",
                room_id="room-1",
                viewer_id="viewer-1",
                source_event_id="evt-1",
                memory_text="likes ramen",
                memory_type="preference",
                confidence=0.8,
                updated_at=10,
                recall_count=1,
                status="active",
                source_kind="auto",
                is_pinned=False,
                stability_score=0.0,
                interaction_value_score=0.0,
                clarity_score=0.0,
                evidence_score=0.0,
            ),
            SimpleNamespace(
                memory_id="mem-2",
                room_id="room-1",
                viewer_id="viewer-2",
                source_event_id="evt-2",
                memory_text="likes noodles",
                memory_type="preference",
                confidence=0.9,
                updated_at=20,
                recall_count=2,
                status="active",
                source_kind="manual",
                is_pinned=True,
                stability_score=0.0,
                interaction_value_score=0.0,
                clarity_score=0.0,
                evidence_score=0.0,
            ),
        ]

        store.prime_memory_index(memories, batch_size=64)

        fake_embedding.embed_texts.assert_called_once_with(["likes ramen", "likes noodles"])
        fake_collection.upsert.assert_called_once()

    def test_prime_memory_index_rebuilds_when_sample_lookup_does_not_match(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_texts.return_value = [[0.1, 0.2], [0.3, 0.4]]
        fake_collection = MagicMock()
        fake_collection.count.return_value = 2
        fake_collection.get.return_value = {
            "ids": ["mem-1"],
            "documents": ["likes ramen"],
            "metadatas": [
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "source_event_id": "evt-1",
                    "memory_text": "likes ramen",
                    "memory_recall_text": "likes ramen",
                    "confidence": 0.8,
                    "updated_at": 10,
                    "recall_count": 1,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                    "stability_score": 0.0,
                    "interaction_value_score": 0.0,
                    "clarity_score": 0.0,
                    "evidence_score": 0.0,
                }
            ],
        }

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.memory_collection = fake_collection
        store._client = MagicMock()
        store._client.get_or_create_collection.return_value = fake_collection

        memories = [
            SimpleNamespace(
                memory_id="mem-1",
                room_id="room-1",
                viewer_id="viewer-1",
                source_event_id="evt-1",
                memory_text="likes ramen",
                memory_type="preference",
                confidence=0.8,
                updated_at=10,
                recall_count=1,
                status="active",
                source_kind="auto",
                is_pinned=False,
                stability_score=0.0,
                interaction_value_score=0.0,
                clarity_score=0.0,
                evidence_score=0.0,
            ),
            SimpleNamespace(
                memory_id="mem-2",
                room_id="room-1",
                viewer_id="viewer-2",
                source_event_id="evt-2",
                memory_text="likes noodles",
                memory_type="preference",
                confidence=0.9,
                updated_at=20,
                recall_count=2,
                status="active",
                source_kind="manual",
                is_pinned=True,
                stability_score=0.0,
                interaction_value_score=0.0,
                clarity_score=0.0,
                evidence_score=0.0,
            ),
        ]

        store.prime_memory_index(memories, batch_size=64)

        fake_collection.get.assert_called_once()
        store._client.delete_collection.assert_called_once()
        fake_embedding.embed_texts.assert_called_once_with(["likes ramen", "likes noodles"])
        fake_collection.upsert.assert_called_once()

    def test_similar_memories_prefers_higher_interaction_value_when_scores_are_close(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()
        fake_collection.query.return_value = {
            "ids": [["m-low", "m-high"]],
            "documents": [["generic context", "cannot eat spicy food"]],
            "metadatas": [[
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "context",
                    "confidence": 0.8,
                    "updated_at": 100,
                    "recall_count": 2,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                    "interaction_value_score": 0.2,
                    "evidence_score": 0.2,
                },
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.8,
                    "updated_at": 90,
                    "recall_count": 2,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                    "interaction_value_score": 0.9,
                    "evidence_score": 0.5,
                },
            ]],
            "distances": [[0.4, 0.4]],
        }

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        result = store.similar_memories("spicy", "room-1", "viewer-1", limit=2)

        self.assertEqual(result[0]["memory_id"], "m-high")

    def test_similar_memories_prefers_higher_evidence_memory_when_scores_are_close(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()
        fake_collection.query.return_value = {
            "ids": [["m-low-evidence", "m-high-evidence"]],
            "documents": [["likes ramen", "likes ramen"]],
            "metadatas": [[
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.8,
                    "updated_at": 100,
                    "recall_count": 1,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                    "interaction_value_score": 0.6,
                    "evidence_score": 0.1,
                },
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.8,
                    "updated_at": 90,
                    "recall_count": 6,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                    "interaction_value_score": 0.6,
                    "evidence_score": 0.9,
                },
            ]],
            "distances": [[0.4, 0.4]],
        }

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        result = store.similar_memories("ramen", "room-1", "viewer-1", limit=2)

        self.assertEqual(result[0]["memory_id"], "m-high-evidence")

    def test_manual_and_pinned_bonus_do_not_beat_far_better_semantic_match(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()
        fake_collection.query.return_value = {
            "ids": [["m-strong-semantic", "m-manual-pinned"]],
            "documents": [["cannot eat spicy food", "likes ramen"]],
            "metadatas": [[
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.75,
                    "updated_at": 100,
                    "recall_count": 1,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                    "interaction_value_score": 0.7,
                    "evidence_score": 0.5,
                },
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.9,
                    "updated_at": 90,
                    "recall_count": 6,
                    "status": "active",
                    "source_kind": "manual",
                    "is_pinned": 1,
                    "interaction_value_score": 0.9,
                    "evidence_score": 0.9,
                },
            ]],
            "distances": [[0.1, 0.8]],
        }

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        result = store.similar_memories("spicy food", "room-1", "viewer-1", limit=2)

        self.assertEqual(result[0]["memory_id"], "m-strong-semantic")

    def test_prime_memory_index_skips_expired_memories(self):
        fake_embedding = MagicMock()
        fake_collection = MagicMock()
        fake_collection.count.return_value = 1
        fake_collection.get.return_value = {
            "ids": ["m-live"],
            "documents": ["likes ramen"],
            "metadatas": [
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "source_event_id": "evt-1",
                    "memory_text": "likes ramen",
                    "memory_recall_text": "likes ramen",
                    "confidence": 0.8,
                    "updated_at": 10,
                    "recall_count": 1,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                    "stability_score": 0.0,
                    "interaction_value_score": 0.0,
                    "clarity_score": 0.0,
                    "evidence_score": 0.0,
                    "expires_at": 0,
                }
            ],
        }

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        memories = [
            SimpleNamespace(
                memory_id="m-live",
                room_id="room-1",
                viewer_id="viewer-1",
                source_event_id="evt-1",
                memory_text="likes ramen",
                memory_type="preference",
                confidence=0.8,
                updated_at=10,
                recall_count=1,
                status="active",
                source_kind="auto",
                is_pinned=False,
                stability_score=0.0,
                interaction_value_score=0.0,
                clarity_score=0.0,
                evidence_score=0.0,
                expires_at=0,
            ),
            SimpleNamespace(
                memory_id="m-expired",
                room_id="room-1",
                viewer_id="viewer-1",
                source_event_id="evt-2",
                memory_text="on a trip",
                memory_type="context",
                confidence=0.5,
                updated_at=10,
                recall_count=1,
                status="active",
                source_kind="auto",
                is_pinned=False,
                stability_score=0.0,
                interaction_value_score=0.0,
                clarity_score=0.0,
                evidence_score=0.0,
                expires_at=1,
            ),
        ]

        with patch("backend.memory.vector_store.time.time", return_value=10):
            store.prime_memory_index(memories)

        self.assertEqual([item["id"] for item in store._memory_items], ["m-live"])

    def test_similar_memories_excludes_expired_metadata(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()
        fake_collection.query.return_value = {
            "ids": [["m-expired", "m-live"]],
            "documents": [["on a trip", "likes ramen"]],
            "metadatas": [[
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "context",
                    "confidence": 0.5,
                    "updated_at": 10,
                    "recall_count": 1,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                    "interaction_value_score": 0.0,
                    "evidence_score": 0.0,
                    "expires_at": 1,
                },
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.8,
                    "updated_at": 10,
                    "recall_count": 1,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                    "interaction_value_score": 0.0,
                    "evidence_score": 0.0,
                    "expires_at": 0,
                },
            ]],
            "distances": [[0.4, 0.4]],
        }

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        with patch("backend.memory.vector_store.time.time", return_value=10):
            result = store.similar_memories("trip", "room-1", "viewer-1", limit=2)

        self.assertEqual([item["memory_id"] for item in result], ["m-live"])

    def test_decay_makes_older_memory_rank_lower_than_recent_one(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()
        now_ms = int(time.time() * 1000)
        one_week_ago_ms = now_ms - (7 * 24 * 3600 * 1000)
        fake_collection.query.return_value = {
            "ids": [["m-old", "m-recent"]],
            "documents": [["鍠滄鎷夐潰", "鍠滄鎷夐潰"]],
            "metadatas": [[
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.8,
                    "updated_at": one_week_ago_ms,
                    "recall_count": 1,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                    "interaction_value_score": 0.0,
                    "evidence_score": 0.0,
                },
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.8,
                    "updated_at": now_ms,
                    "recall_count": 1,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                    "interaction_value_score": 0.0,
                    "evidence_score": 0.0,
                },
            ]],
            "distances": [[0.4, 0.4]],
        }

        store = VectorMemory("data/chroma", settings=make_settings(decay_halflife_hours=168.0), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        result = store.similar_memories("鎷夐潰", "room-1", "viewer-1", limit=2)

        self.assertEqual(result[0]["memory_id"], "m-recent")

    def test_pinned_memory_is_exempt_from_decay(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()
        now_ms = int(time.time() * 1000)
        one_week_ago_ms = now_ms - (7 * 24 * 3600 * 1000)
        fake_collection.query.return_value = {
            "ids": [["m-old-pinned", "m-recent"]],
            "documents": [["鍠滄鎷夐潰", "鍠滄鎷夐潰"]],
            "metadatas": [[
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.8,
                    "updated_at": one_week_ago_ms,
                    "recall_count": 1,
                    "status": "active",
                    "source_kind": "manual",
                    "is_pinned": 1,
                    "interaction_value_score": 0.0,
                    "evidence_score": 0.0,
                },
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.8,
                    "updated_at": now_ms,
                    "recall_count": 1,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                    "interaction_value_score": 0.0,
                    "evidence_score": 0.0,
                },
            ]],
            "distances": [[0.4, 0.4]],
        }

        store = VectorMemory("data/chroma", settings=make_settings(decay_halflife_hours=168.0), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        result = store.similar_memories("鎷夐潰", "room-1", "viewer-1", limit=2)

        self.assertEqual(result[0]["memory_id"], "m-old-pinned")

    def test_no_decay_when_halflife_is_zero(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()
        now_ms = int(time.time() * 1000)
        one_week_ago_ms = now_ms - (7 * 24 * 3600 * 1000)
        fake_collection.query.return_value = {
            "ids": [["m-old", "m-recent"]],
            "documents": [["鍠滄鎷夐潰", "鍠滄鎷夐潰"]],
            "metadatas": [[
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.8,
                    "updated_at": one_week_ago_ms,
                    "recall_count": 1,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                    "interaction_value_score": 0.0,
                    "evidence_score": 0.0,
                },
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.8,
                    "updated_at": now_ms,
                    "recall_count": 1,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                    "interaction_value_score": 0.0,
                    "evidence_score": 0.0,
                },
            ]],
            "distances": [[0.4, 0.4]],
        }

        store = VectorMemory("data/chroma", settings=make_settings(decay_halflife_hours=0), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        result = store.similar_memories("鎷夐潰", "room-1", "viewer-1", limit=2)

        # When no decay, both have same final_score so updated_at breaks the tie;
        # the key point is that old memory is NOT penalised by time decay.
        old_score = store._final_rank_key(result[0] if result[0]["memory_id"] == "m-old" else result[1], "鎷夐潰", 0)
        recent_score = store._final_rank_key(result[0] if result[0]["memory_id"] == "m-recent" else result[1], "鎷夐潰", 0)
        self.assertEqual(old_score[0], recent_score[0])

    def test_last_recalled_at_slows_decay(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()
        now_ms = int(time.time() * 1000)
        one_week_ago_ms = now_ms - (7 * 24 * 3600 * 1000)
        fake_collection.query.return_value = {
            "ids": [["m-old-recalled", "m-old-not-recalled"]],
            "documents": [["鍠滄鎷夐潰", "鍠滄鎷夐潰"]],
            "metadatas": [[
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.8,
                    "updated_at": one_week_ago_ms,
                    "last_recalled_at": now_ms,
                    "recall_count": 3,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                    "interaction_value_score": 0.0,
                    "evidence_score": 0.0,
                },
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.8,
                    "updated_at": one_week_ago_ms,
                    "last_recalled_at": 0,
                    "recall_count": 0,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                    "interaction_value_score": 0.0,
                    "evidence_score": 0.0,
                },
            ]],
            "distances": [[0.4, 0.4]],
        }

        store = VectorMemory("data/chroma", settings=make_settings(decay_halflife_hours=168.0), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        result = store.similar_memories("鎷夐潰", "room-1", "viewer-1", limit=2)

        self.assertEqual(result[0]["memory_id"], "m-old-recalled")


if __name__ == "__main__":
    unittest.main()


