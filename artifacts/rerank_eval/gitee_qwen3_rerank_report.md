# Gitee Qwen3 Reranker 直播记忆话风测试报告

## 测试目标

验证在线 `Qwen3-Reranker-0.6B` 在直播弹幕 + 观众长期记忆候选上的排序能力，重点覆盖饮品、忌口、护肤、宠物、工作城市、住处、食物偏好和闲聊无召回场景。

## 汇总指标

- 总 case 数：16
- 有明确相关记忆 case：15
- 无应召回记忆 case：1
- Top1 命中率：93.33% (14/15)
- Top3 命中率：100.00% (15/15)
- 平均延迟：308.15 ms
- 最大延迟：501.98 ms

## Case 明细

### drink_coffee_vs_other_drinks（饮品偏好-咖啡细粒度）

- 状态：通过
- 延迟：415.43 ms
- 期望相关 index：[1]
- Top1 index：1，score：0.9999606609344482
- Top1 文档：观众记忆｜饮品习惯｜置信度：高

### tea_oolong_vs_tea_family（饮品偏好-茶类细粒度）

- 状态：通过
- 延迟：303.72 ms
- 期望相关 index：[1]
- Top1 index：1，score：0.9999613761901855
- Top1 文档：观众记忆｜茶饮偏好｜置信度：高

### spicy_cannot_vs_like_hotpot（饮食限制-辣度细粒度）

- 状态：通过
- 延迟：259.91 ms
- 期望相关 index：[2]
- Top1 index：2，score：0.9999710321426392
- Top1 文档：观众记忆｜饮食限制｜置信度：高

### cilantro_vs_green_foods（饮食限制-配菜忌口）

- 状态：通过
- 延迟：265.99 ms
- 期望相关 index：[0]
- Top1 index：0，score：0.9999076128005981
- Top1 文档：观众记忆｜饮食忌口｜置信度：高

### skincare_sensitive_vs_sunscreen（护肤状态-敏感肌）

- 状态：通过
- 延迟：276.18 ms
- 期望相关 index：[2]
- Top1 index：2，score：0.9999712705612183
- Top1 文档：观众记忆｜皮肤状态｜置信度：高

### sunscreen_vs_facecream（护肤场景-防晒召回）

- 状态：未通过
- 延迟：297.1 ms
- 期望相关 index：[1]
- Top1 index：2，score：0.9995299577713013
- Top1 文档：观众记忆｜出游习惯｜置信度：中

### pet_cat_vs_other_pets（宠物记忆-猫狗细分）

- 状态：通过
- 延迟：323.49 ms
- 期望相关 index：[1]
- Top1 index：1，score：0.9998993873596191
- Top1 文档：观众记忆｜家庭宠物｜置信度：高

### frontend_job_vs_generic_work（职业记忆-岗位细粒度）

- 状态：通过
- 延迟：322.93 ms
- 期望相关 index：[0]
- Top1 index：0，score：0.9998903274536133
- Top1 文档：观众记忆｜职业身份｜置信度：高

### living_company_near_vs_city（地点记忆-居住与城市区分）

- 状态：通过
- 延迟：254.09 ms
- 期望相关 index：[1]
- Top1 index：1，score：0.9998762607574463
- Top1 文档：观众记忆｜居住通勤｜置信度：高

### ramen_vs_other_noodles（食物偏好-面类细分）

- 状态：通过
- 延迟：292.66 ms
- 期望相关 index：[1]
- Top1 index：1，score：0.9999687671661377
- Top1 文档：观众记忆｜食物偏好｜置信度：高

### junk_should_score_low（闲聊-无召回）

- 状态：通过
- 延迟：501.98 ms
- 期望相关 index：无明确相关记忆
- Top1 index：3，score：0.00028156847110949457
- Top1 文档：观众记忆｜皮肤状态｜置信度：高

### negative_food_vs_positive_food（正负偏好冲突）

- 状态：通过
- 延迟：270.5 ms
- 期望相关 index：[1]
- Top1 index：1，score：0.9999780654907227
- Top1 文档：观众记忆｜饮食限制｜置信度：高

### old_memory_context_current_comment（当前语境覆盖旧记忆噪声）

- 状态：通过
- 延迟：271.89 ms
- 期望相关 index：[0]
- Top1 index：0，score：0.9999555349349976
- Top1 文档：观众记忆｜食物偏好｜置信度：高

### memory_expansion_like_recall（扩写记忆-同义表达）

- 状态：通过
- 延迟：291.66 ms
- 期望相关 index：[0]
- Top1 index：0，score：0.999955415725708
- Top1 文档：观众记忆｜工作压力｜置信度：高

### hard_multi_memory_same_user（多条同用户记忆-精确意图）

- 状态：通过
- 延迟：265.19 ms
- 期望相关 index：[0]
- Top1 index：0，score：0.9996278285980225
- Top1 文档：观众记忆｜职业工作流｜置信度：高

### hard_opposite_polarity_same_keywords（同关键词相反极性）

- 状态：通过
- 延迟：317.73 ms
- 期望相关 index：[1]
- Top1 index：1，score：0.9999831914901733
- Top1 文档：观众记忆｜香氛避雷｜置信度：高
