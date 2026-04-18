"""LLM-backed viewer memory extraction protocol layer."""

from __future__ import annotations

import json

from backend.schemas.live import LiveEvent


ALLOWED_MEMORY_TYPES = {"preference", "fact", "context"}
ALLOWED_POLARITIES = {"positive", "negative", "neutral"}
MEMORY_TYPE_CONFIDENCE = {
    "preference": 0.86,
    "context": 0.78,
    "fact": 0.74,
}
NEGATIVE_TEXT_SIGNALS = (
    "不喜欢",
    "不爱",
    "不想",
    "不吃",
    "不喝",
    "不买",
    "不再",
    "讨厌",
    "反感",
    "拒绝",
    "不能吃",
    "不能喝",
    "忌口",
    "接受不了",
)

BASE_SYSTEM_PROMPT = (
    "你是直播场景记忆抽取器。只抽取对主播后续互动有用、可长期复用的观众记忆。"
    "只返回合法 JSON，不要 markdown，不要额外解释。"
    "JSON 字段必须包含 should_extract,memory_text,memory_type,polarity,temporal_scope,reason。"
    "如果信息只是短期计划、短期情绪、寒暄、刷屏、交易问句，应该返回 should_extract=false。"
    "\n\n"
    "标注规则\n"
    "- fact = 稳定客观事实、长期重复习惯、生理条件、现实约束或能力情况。只要不是明确的喜欢/讨厌，优先标成 fact。\n"
    "- context = 稳定背景信息，如身份、角色、居住地、所在城市、职业、家庭状态、人生阶段。像“现在在苏州带娃”这类持续性角色应标为 context。\n"
    "- preference = 明确的喜欢/不喜欢、偏好选择、长期回避项、稳定选择标准。\n"
    "- negative polarity 只有在文本明确表达讨厌、回避、拒绝，或饮食限制作为偏好时才使用。\n"
    "- 像“不能吃辣”“不能喝冰的”“忌口海鲜”这类会直接影响推荐的饮食限制，应标为 preference + negative。\n"
    "- 像“对猫毛过敏”这种生理事实应标为 fact + neutral，而不是 preference + negative。\n"
    "- 长期习惯不自动等于 preference。作息、通勤时长、养宠物、运动频率通常更接近 fact，除非文本明确出现喜欢/讨厌。\n"
    "- 如果一句话同时包含过去经历和当前稳定角色，优先抽取当前持续成立的角色背景。比如“去年刚毕业，现在在做产品助理”应保留“现在在做产品助理”。\n"
    "- memory_text 要尽量简洁，但不能丢掉关键主语信息。像“家里”“租房住在”“对猫毛”这类会影响复用的信息不要随意删掉。\n"
    "- 含有“最近/今天/今晚/这两周/过两天/下个月”这类时间限定的内容，通常是 short_term，除非句子同时明确说明它是长期稳定状态。\n"
    "\n"
    "少样本示例\n"
    "示例1：一直喝无糖可乐\n"
    "输入：我一直都喝无糖可乐\n"
    '输出：{"should_extract":true,"memory_text":"喜欢喝无糖可乐","memory_type":"preference","polarity":"positive","temporal_scope":"long_term","reason":"稳定的长期饮品偏好"}\n'
    "\n"
    "示例2：一点都不喜欢香菜\n"
    "输入：我一点都不喜欢香菜\n"
    '输出：{"should_extract":true,"memory_text":"不喜欢香菜","memory_type":"preference","polarity":"negative","temporal_scope":"long_term","reason":"明确的长期负向口味偏好"}\n'
    "\n"
    "示例3：在杭州做前端开发\n"
    "输入：我在杭州做前端开发\n"
    '输出：{"should_extract":true,"memory_text":"在杭州做前端开发","memory_type":"context","polarity":"neutral","temporal_scope":"long_term","reason":"稳定背景信息，可长期复用"}\n'
    "\n"
    "示例4：今晚下班准备去吃火锅\n"
    "输入：今晚下班准备去吃火锅\n"
    '输出：{"should_extract":false,"memory_text":"","memory_type":"context","polarity":"neutral","temporal_scope":"short_term","reason":"短期计划，不适合保留为长期记忆"}\n'
    "\n"
    "示例5：来了哈哈哈\n"
    "输入：来了哈哈哈\n"
    '输出：{"should_extract":false,"memory_text":"","memory_type":"context","polarity":"neutral","temporal_scope":"short_term","reason":"低信号寒暄，缺少可复用记忆"}\n'
    "\n"
    "示例6：这个多少钱，链接在哪\n"
    "输入：这个多少钱，链接在哪\n"
    '输出：{"should_extract":false,"memory_text":"","memory_type":"context","polarity":"neutral","temporal_scope":"short_term","reason":"交易问句，不是观众长期记忆"}\n'
    "\n"
    "示例7：家里养了两只猫\n"
    "输入：我家里养了两只猫\n"
    '输出：{"should_extract":true,"memory_text":"家里养了两只猫","memory_type":"fact","polarity":"neutral","temporal_scope":"long_term","reason":"稳定的客观生活事实，可长期复用"}\n'
    "\n"
    "示例8：平时凌晨一点以后才睡\n"
    "输入：我平时都是凌晨一点以后才睡\n"
    '输出：{"should_extract":true,"memory_text":"平时凌晨一点以后才睡","memory_type":"fact","polarity":"neutral","temporal_scope":"long_term","reason":"长期稳定作息习惯，属于客观事实而非偏好"}\n'
    "\n"
    "示例9：一直都只用安卓手机\n"
    "输入：我一直都只用安卓手机\n"
    '输出：{"should_extract":true,"memory_text":"一直都只用安卓手机","memory_type":"preference","polarity":"positive","temporal_scope":"long_term","reason":"稳定的设备选择偏好，可长期复用"}\n'
    "\n"
    "示例10：不是不喜欢猫，只是对猫毛过敏\n"
    "输入：我不是不喜欢猫，我只是对猫毛过敏\n"
    '输出：{"should_extract":true,"memory_text":"对猫毛过敏","memory_type":"fact","polarity":"neutral","temporal_scope":"long_term","reason":"长期稳定的生理事实，不是负向偏好"}\n'
    "\n"
    "示例11：租房住在公司附近\n"
    "输入：我租房住在公司附近\n"
    '输出：{"should_extract":true,"memory_text":"租房住在公司附近","memory_type":"context","polarity":"neutral","temporal_scope":"long_term","reason":"稳定居住背景信息，可长期复用"}\n'
    "\n"
    "示例12：最近两周都在上海出差\n"
    "输入：我最近两周都在上海出差\n"
    '输出：{"should_extract":false,"memory_text":"","memory_type":"context","polarity":"neutral","temporal_scope":"short_term","reason":"带有最近两周的时间限定，属于短期状态"}\n'
    "\n"
    "示例13：每天通勤都要坐一个小时地铁\n"
    "输入：我每天通勤都要坐一个小时地铁\n"
    '输出：{"should_extract":true,"memory_text":"每天通勤要坐一个小时地铁","memory_type":"fact","polarity":"neutral","temporal_scope":"long_term","reason":"长期稳定通勤事实，不是偏好"}\n'
    "\n"
    "示例14：平时很少吃外卖，基本都自己做饭\n"
    "输入：我平时很少吃外卖，基本都自己做饭\n"
    '输出：{"should_extract":true,"memory_text":"平时很少吃外卖，基本都自己做饭","memory_type":"fact","polarity":"neutral","temporal_scope":"long_term","reason":"稳定生活方式事实，不应脑补成负向偏好"}\n'
    "\n"
    "示例15：周末一般都会去西湖边夜跑\n"
    "输入：我周末一般都会去西湖边夜跑\n"
    '输出：{"should_extract":true,"memory_text":"周末一般都会去西湖边夜跑","memory_type":"fact","polarity":"neutral","temporal_scope":"long_term","reason":"重复出现的长期活动习惯，属于事实而非偏好"}\n'
    "\n"
    "示例16：现在在苏州带娃\n"
    "输入：我现在在苏州带娃\n"
    '输出：{"should_extract":true,"memory_text":"现在在苏州带娃","memory_type":"context","polarity":"neutral","temporal_scope":"long_term","reason":"稳定的家庭角色和生活背景信息，可长期复用"}\n'
    "\n"
    "示例17：不是很能吃辣\n"
    "输入：我不是很能吃辣\n"
    '输出：{"should_extract":true,"memory_text":"不太能吃辣","memory_type":"preference","polarity":"negative","temporal_scope":"long_term","reason":"稳定的饮食限制，适合作为负向口味偏好长期复用"}\n'
    "\n"
    "示例18：去年刚毕业，现在在做产品助理\n"
    "输入：我去年刚毕业，现在在做产品助理\n"
    '输出：{"should_extract":true,"memory_text":"现在在做产品助理","memory_type":"context","polarity":"neutral","temporal_scope":"long_term","reason":"当前职业身份是稳定背景信息，应优先保留当前角色"}'
)

COT_SUFFIX = (
    "\n\n"
    "在作答前请先在内部逐步思考："
    "1）先判断这条信息是否稳定、是否值得长期记忆；"
    "2）如果值得保留，再抽取最小但可复用的 memory_text；"
    "3）再判断 memory_type、polarity 和 temporal_scope；"
    "4）最后检查所有字段是否合法。"
    "不要暴露你的思考过程，只输出一个合法 JSON 对象。"
)


class LLMBackedViewerMemoryExtractor:
    def __init__(self, settings, runtime):
        self._settings = settings
        self._runtime = runtime

    def extract(self, event: LiveEvent):
        payload = self.extract_payload(event)
        return self._normalize(payload)

    def extract_payload(self, event: LiveEvent):
        if event.event_type != "comment":
            return {}

        viewer_id = event.user.viewer_id
        content = str(event.content or "").strip()
        if not viewer_id or not content:
            return {}

        response_text = self._runtime.infer_json(
            system_prompt=self._system_prompt(),
            user_prompt=self._user_prompt(event, viewer_id, content),
        )
        return json.loads(response_text)

    def _normalize(self, payload):
        if not isinstance(payload, dict):
            return []
        if payload.get("should_extract") is not True:
            return []

        temporal_scope = str(payload.get("temporal_scope", "")).strip().lower()
        if temporal_scope != "long_term":
            return []

        polarity = payload.get("polarity")
        if not self._is_non_empty_string(polarity):
            return []
        polarity = polarity.strip().lower()
        if polarity not in ALLOWED_POLARITIES:
            return []

        memory_type = str(payload.get("memory_type", "")).strip().lower()
        if memory_type not in ALLOWED_MEMORY_TYPES:
            return []

        memory_text = payload.get("memory_text")
        if not self._is_non_empty_string(memory_text):
            return []
        memory_text = memory_text.strip()

        reason = payload.get("reason")
        if not self._is_non_empty_string(reason):
            return []

        if polarity == "negative" and not self._has_negative_signal(memory_text):
            return []

        confidence = MEMORY_TYPE_CONFIDENCE[memory_type]
        return [
            {
                "memory_text": memory_text,
                "memory_type": memory_type,
                "confidence": confidence,
            }
        ]

    def _system_prompt(self):
        if self._prompt_variant() == "baseline":
            return BASE_SYSTEM_PROMPT
        return BASE_SYSTEM_PROMPT + COT_SUFFIX

    def _prompt_variant(self):
        variant = str(getattr(self._settings, "memory_extractor_prompt_variant", "cot") or "").strip().lower()
        if variant == "baseline":
            return "baseline"
        return "cot"

    @staticmethod
    def _user_prompt(event: LiveEvent, viewer_id: str, content: str):
        payload = {
            "event": {
                "event_id": event.event_id,
                "room_id": event.room_id,
                "viewer_id": viewer_id,
                "nickname": event.user.nickname,
                "content": content,
                "ts": event.ts,
            }
        }
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _is_non_empty_string(value):
        return isinstance(value, str) and bool(value.strip())

    @staticmethod
    def _has_negative_signal(text: str):
        return any(signal in text for signal in NEGATIVE_TEXT_SIGNALS)
