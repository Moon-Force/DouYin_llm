# Semantic Recall Report

## Summary

- Dataset: `tests/fixtures/semantic_recall/blind_100.json`
- Cases: 100
- Top1: 47/100 (0.4700)
- Top3: 100/100 (1.0000)

## blind-001

- Tags: typo
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 最近写页面经常熬页赶进度

**Expected Memory**

> 我在杭州做前端开发，最近连续两周都在加班赶需求。

**Top 3 Recalled**

1. 我在杭州做前端开发，最近连续一个月都在加班赶需求。
2. 我在杭州做前端开发，最近连续两周都在加班赶需求。
3. 我在上海做前端开发，最近连续两周都在加班赶需求。

## blind-002

- Tags: typo
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 礼拜三总是开汇拖到很晚才下般

**Expected Memory**

> 我在苏州做产品经理，每周三固定开周会到很晚。

**Top 3 Recalled**

1. 我在苏州做项目经理，每周三固定开周会到很晚。
2. 我在上海做产品经理，每周三固定开周会到很晚。
3. 我在苏州做产品经理，每周三固定开周会到很晚。

## blind-003

- Tags: typo
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 最近医院页般很多，作息全乱了

**Expected Memory**

> 我在宁波医院做护士，这个月夜班排得特别密。

**Top 3 Recalled**

1. 我在宁波医院做医生，这个月夜班排得特别密。
2. 我在宁波医院做护士，上个月夜班排得特别密。
3. 我在宁波医院做护士，这个月夜班排得特别密。

## blind-004

- Tags: typo
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就那个，月底带新人做账，经常忙到很晚

**Expected Memory**

> 我在合肥做会计，月底结账那几天经常要培训新人到很晚。

**Top 3 Recalled**

1. 我在南京做会计，月底结账那几天经常要培训新人到很晚。
2. 我在合肥做会计，月底结账那几天经常要培训新人到很晚。
3. 我在合肥做出纳，月底对账那几天经常要培训新人到很晚。

## blind-005

- Tags: typo
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 这阵子天天都在改公开刻的教雪方案

**Expected Memory**

> 我在武汉幼儿园当老师，最近一直在改公开课教案。

**Top 3 Recalled**

1. 我在长沙幼儿园当老师，最近一直在改公开课教案。
2. 我在武汉小学当老师，最近一直在改公开课教案。
3. 我在武汉幼儿园当老师，最近一直在改公开课教案。

## blind-006

- Tags: typo
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 休息天汇绕着西湖炮长距离

**Expected Memory**

> 我周末常去西湖边夜跑，一次差不多十公里。

**Top 3 Recalled**

1. 我工作日下班后会去西湖夜跑，一次差不多十公里。
2. 我周末常去西湖边夜跑，一次差不多十公里。
3. 我周末常去西湖边夜跑，一次差不多五公里。

## blind-007

- Tags: typo
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 一喝乃制品胃就很难受

**Expected Memory**

> 我乳糖不耐，喝牛奶就容易肚子不舒服。

**Top 3 Recalled**

1. 我乳糖不耐，喝牛奶就容易肚子不舒服。
2. 我乳糖不耐，喝酸奶就容易肚子不舒服。
3. 我乳糖不耐，只有空腹喝牛奶才会肚子不舒服。

## blind-008

- Tags: typo
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 就那个，晚上基本都在刷雅思词汇和听力

**Expected Memory**

> 我最近在备考雅思，晚上下班后会背单词做听力。

**Top 3 Recalled**

1. 我最近在备考雅思，晚上下班后会背单词做听力。
2. 我最近在备考雅思，晚上下班后会刷口语题不怎么做听力。
3. 我最近在备考雅思，晚上下班后主要做阅读和写作。

## blind-009

- Tags: typo
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就那个，家里那只叫团子的橘猫今天又拆家了

**Expected Memory**

> 我养了一只橘猫，名字叫团子，特别能吃。

**Top 3 Recalled**

1. 我养了一只橘猫，名字叫团子，最近在控制体重吃得不多。
2. 我养了一只橘猫，名字叫团子，特别能吃。
3. 我养了两只猫，其中一只叫团子，但不是橘猫。

## blind-010

- Tags: typo
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 就那个，虽然一直拿苹果手机，但下次想试试折叠机

**Expected Memory**

> 我一直用iPhone，不过下一台手机想换折叠屏。

**Top 3 Recalled**

1. 我一直用iPhone，不过下一台手机想换折叠屏。
2. 我一直用华为，不过下一台手机想换折叠屏。
3. 我一直用iPhone，不过下一台手机想换游戏手机。

## blind-011

- Tags: typo
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就那个，辣锅可以，但凡是香菜我一口都不碰

**Expected Memory**

> 我喜欢吃重辣火锅，但是一点都不吃香菜。

**Top 3 Recalled**

1. 我喜欢吃微辣火锅，但是一点都不吃香菜。
2. 我喜欢吃重辣火锅，但是一点都不吃香菜。
3. 我喜欢吃麻辣烫，口味要重辣，但香菜我不吃。

## blind-012

- Tags: typo
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 一到换季脸上就特别干还汇起皮

**Expected Memory**

> 我皮肤偏干，换季的时候脸上很容易起皮。

**Top 3 Recalled**

1. 我皮肤偏干，换季的时候脸上很容易起皮。
2. 我皮肤偏干，换季的时候脸上很容易泛红不太起皮。
3. 我皮肤偏干，换季的时候主要是嘴角起皮。

## blind-013

- Tags: typo
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就那个，最近控制体重，晚上基本不碰主食了

**Expected Memory**

> 我最近在减脂，晚饭尽量不吃米饭和面。

**Top 3 Recalled**

1. 我最近在减脂，晚饭尽量不吃油炸和甜食。
2. 我最近在减脂，晚饭尽量不吃米饭和面。
3. 我最近在减脂，晚饭会吃少量米饭，不再完全戒掉。

## blind-014

- Tags: typo
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就那个，早上通常就一杯黑咖啡，甜口的都不太碰

**Expected Memory**

> 我早饭一般只喝美式咖啡，不怎么吃甜的。

**Top 3 Recalled**

1. 我早饭一般只喝拿铁咖啡，不怎么吃甜的。
2. 我早饭一般只喝美式咖啡，不怎么吃甜的。
3. 我早饭一般只喝美式咖啡，偶尔会加糖和奶。

## blind-015

- Tags: typo
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 虾蟹这种孩鲜我吃了汇过敏起疹子

**Expected Memory**

> 我对海鲜过敏，尤其虾蟹一吃就起疹子。

**Top 3 Recalled**

1. 我对海鲜过敏，尤其虾蟹一吃就起疹子。
2. 我对海鲜过敏，去年吃虾蟹才起疹子。
3. 我对海鲜过敏，虾还能吃一点，螃蟹一吃就起疹子。

## blind-016

- Tags: typo
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 六月想飞去日本看现场演楚

**Expected Memory**

> 我准备六月去日本看演唱会，机票已经在看了。

**Top 3 Recalled**

1. 我准备六月去日本看演唱会，机票已经在看了。
2. 我准备六月去日本看演唱会，机票已经买好了。
3. 我准备六月去日本看音乐节，机票已经在看了。

## blind-017

- Tags: typo
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 这个月又得炮上孩谈事情了

**Expected Memory**

> 我每个月都要去上海出差两三次，最近尤其频繁。

**Top 3 Recalled**

1. 我每个月都要去上海出差一两次，最近尤其频繁。
2. 我每个月都要去上海出差两三次，上个月尤其频繁。
3. 我每个月都要去上海出差两三次，最近尤其频繁。

## blind-018

- Tags: typo
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 白天还得往医愿炮着照顾妈妈

**Expected Memory**

> 我妈妈最近住院了，我白天要来回照顾她。

**Top 3 Recalled**

1. 我妈妈最近住院了，我白天要来回照顾她。
2. 我妈妈最近住院了，我白天主要去医院帮她办理检查。
3. 我妈妈最近在家休养，我白天要来回照顾她。

## blind-019

- Tags: typo
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就那个，休息天基本都在准备教资考试

**Expected Memory**

> 我准备十二月考教师资格证，周末都在刷题。

**Top 3 Recalled**

1. 我准备十二月考教师资格证，平时晚上复习，周末反而休息。
2. 我准备十二月考教师资格证，周末都在刷题。
3. 我准备十一月考教师资格证，周末都在刷题。

## blind-020

- Tags: typo
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 就那个，十一月想去成都待几天放松一下

**Expected Memory**

> 我打算十一月去成都玩一周，酒店都快订好了。

**Top 3 Recalled**

1. 我打算十一月去成都玩一周，酒店都快订好了。
2. 我打算十一月去成都玩三天，酒店都快订好了。
3. 我打算十一月去成都玩一周，酒店已经订好了。

## blind-021

- Tags: spoken
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 就那个，最近写页面经常熬夜赶进度嘛

**Expected Memory**

> 我在杭州做前端开发，最近连续两周都在加班赶需求。

**Top 3 Recalled**

1. 我在杭州做前端开发，最近连续两周都在加班赶需求。
2. 我在上海做前端开发，最近连续两周都在加班赶需求。
3. 我在杭州做前端开发，最近连续一个月都在加班赶需求。

## blind-022

- Tags: spoken
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就那个，礼拜三总是开会拖到很晚才下班嘛

**Expected Memory**

> 我在苏州做产品经理，每周三固定开周会到很晚。

**Top 3 Recalled**

1. 我在苏州做项目经理，每周三固定开周会到很晚。
2. 我在上海做产品经理，每周三固定开周会到很晚。
3. 我在苏州做产品经理，每周三固定开周会到很晚。

## blind-023

- Tags: spoken
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就那个，我在宁波医院当护士，这个月夜班排得太密了，作息全乱了嘛

**Expected Memory**

> 我在宁波医院做护士，这个月夜班排得特别密。

**Top 3 Recalled**

1. 我在宁波医院做护士，上个月夜班排得特别密。
2. 我在宁波医院做护士，这个月夜班排得特别密。
3. 我在宁波医院做护士，这个月夜班排得很松。

## blind-024

- Tags: spoken
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就那个，月底带新人做账，经常忙到很晚嘛

**Expected Memory**

> 我在合肥做会计，月底结账那几天经常要培训新人到很晚。

**Top 3 Recalled**

1. 我在南京做会计，月底结账那几天经常要培训新人到很晚。
2. 我在合肥做会计，月底结账那几天经常要培训新人到很晚。
3. 我在合肥做出纳，月底对账那几天经常要培训新人到很晚。

## blind-025

- Tags: spoken
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就那个，这阵子天天都在改公开课的教学方案嘛

**Expected Memory**

> 我在武汉幼儿园当老师，最近一直在改公开课教案。

**Top 3 Recalled**

1. 我在武汉小学当老师，最近一直在改公开课教案。
2. 我在长沙幼儿园当老师，最近一直在改公开课教案。
3. 我在武汉幼儿园当老师，最近一直在改公开课教案。

## blind-026

- Tags: spoken
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就那个，休息天会绕着西湖跑长距离嘛

**Expected Memory**

> 我周末常去西湖边夜跑，一次差不多十公里。

**Top 3 Recalled**

1. 我工作日下班后会去西湖夜跑，一次差不多十公里。
2. 我周末常去西湖边夜跑，一次差不多十公里。
3. 我周末常去西湖边夜跑，一次差不多五公里。

## blind-027

- Tags: spoken
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 就那个，一喝奶制品胃就很难受嘛

**Expected Memory**

> 我乳糖不耐，喝牛奶就容易肚子不舒服。

**Top 3 Recalled**

1. 我乳糖不耐，喝牛奶就容易肚子不舒服。
2. 我乳糖不耐，只有空腹喝牛奶才会肚子不舒服。
3. 我乳糖不耐，喝奶茶比喝纯牛奶更容易不舒服。

## blind-028

- Tags: spoken
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 就那个，晚上基本都在刷雅思词汇和听力嘛

**Expected Memory**

> 我最近在备考雅思，晚上下班后会背单词做听力。

**Top 3 Recalled**

1. 我最近在备考雅思，晚上下班后会背单词做听力。
2. 我最近在备考雅思，晚上下班后会刷口语题不怎么做听力。
3. 我最近在备考雅思，晚上下班后会背单词但不做听力。

## blind-029

- Tags: spoken
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就那个，家里那只叫团子的橘猫今天又拆家了嘛

**Expected Memory**

> 我养了一只橘猫，名字叫团子，特别能吃。

**Top 3 Recalled**

1. 我养了一只橘猫，名字叫团子，最近在控制体重吃得不多。
2. 我养了两只猫，其中一只叫团子，但不是橘猫。
3. 我养了一只橘猫，名字叫团子，特别能吃。

## blind-030

- Tags: spoken
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 就那个，虽然一直拿苹果手机，但下次想试试折叠机嘛

**Expected Memory**

> 我一直用iPhone，不过下一台手机想换折叠屏。

**Top 3 Recalled**

1. 我一直用iPhone，不过下一台手机想换折叠屏。
2. 我一直用华为，不过下一台手机想换折叠屏。
3. 我一直用iPhone，不过下一台手机想换游戏手机。

## blind-031

- Tags: spoken
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就那个，辣锅可以，但凡是香菜我一口都不碰嘛

**Expected Memory**

> 我喜欢吃重辣火锅，但是一点都不吃香菜。

**Top 3 Recalled**

1. 我喜欢吃微辣火锅，但是一点都不吃香菜。
2. 我喜欢吃重辣火锅，但是一点都不吃香菜。
3. 我喜欢吃麻辣烫，口味要重辣，但香菜我不吃。

## blind-032

- Tags: spoken
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 就那个，一到换季脸上就特别干还会起皮嘛

**Expected Memory**

> 我皮肤偏干，换季的时候脸上很容易起皮。

**Top 3 Recalled**

1. 我皮肤偏干，换季的时候脸上很容易起皮。
2. 我皮肤偏干，换季的时候脸上会紧绷但不太脱皮。
3. 我皮肤偏干，换季的时候脸上很容易泛红不太起皮。

## blind-033

- Tags: spoken
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就那个，最近控制体重，晚上基本不碰主食了嘛

**Expected Memory**

> 我最近在减脂，晚饭尽量不吃米饭和面。

**Top 3 Recalled**

1. 我最近在减脂，晚饭尽量不吃油炸和甜食。
2. 我最近在减脂，晚饭尽量不吃米饭和面。
3. 我最近在减脂，晚饭会吃少量米饭，不再完全戒掉。

## blind-034

- Tags: spoken
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就那个，早上通常就一杯黑咖啡，甜口的都不太碰嘛

**Expected Memory**

> 我早饭一般只喝美式咖啡，不怎么吃甜的。

**Top 3 Recalled**

1. 我早饭一般只喝拿铁咖啡，不怎么吃甜的。
2. 我早饭一般只喝美式咖啡，不怎么吃甜的。
3. 我早饭一般只喝美式咖啡，偶尔会加糖和奶。

## blind-035

- Tags: spoken
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 就那个，虾蟹这种海鲜我吃了会过敏起疹子嘛

**Expected Memory**

> 我对海鲜过敏，尤其虾蟹一吃就起疹子。

**Top 3 Recalled**

1. 我对海鲜过敏，尤其虾蟹一吃就起疹子。
2. 我对海鲜过敏，去年吃虾蟹才起疹子。
3. 我对海鲜过敏，虾还能吃一点，螃蟹一吃就起疹子。

## blind-036

- Tags: spoken
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就那个，六月想飞去日本看现场演出嘛

**Expected Memory**

> 我准备六月去日本看演唱会，机票已经在看了。

**Top 3 Recalled**

1. 我准备六月去日本看演唱会，机票已经买好了。
2. 我准备六月去日本看演唱会，机票已经在看了。
3. 我准备六月去日本看音乐节，机票已经在看了。

## blind-037

- Tags: spoken
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就那个，这个月又得跑上海谈事情了嘛

**Expected Memory**

> 我每个月都要去上海出差两三次，最近尤其频繁。

**Top 3 Recalled**

1. 我每个月都要去上海出差两三次，主要是当天往返开会。
2. 我每个月都要去上海出差一两次，最近尤其频繁。
3. 我每个月都要去上海出差两三次，最近尤其频繁。

## blind-038

- Tags: spoken
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 就那个，白天还得往医院跑着照顾妈妈嘛

**Expected Memory**

> 我妈妈最近住院了，我白天要来回照顾她。

**Top 3 Recalled**

1. 我妈妈最近住院了，我白天要来回照顾她。
2. 我妈妈最近住院了，我白天主要去医院帮她办理检查。
3. 我妈妈最近在家休养，我白天要来回照顾她。

## blind-039

- Tags: spoken
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就那个，休息天基本都在准备教资考试嘛

**Expected Memory**

> 我准备十二月考教师资格证，周末都在刷题。

**Top 3 Recalled**

1. 我准备十二月考教师资格证，平时晚上复习，周末反而休息。
2. 我准备十二月考教师资格证，周末都在刷题。
3. 我准备十一月考教师资格证，周末都在刷题。

## blind-040

- Tags: spoken
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 就那个，十一月想去成都待几天放松一下嘛

**Expected Memory**

> 我打算十一月去成都玩一周，酒店都快订好了。

**Top 3 Recalled**

1. 我打算十一月去成都玩一周，酒店都快订好了。
2. 我打算十一月去成都玩三天，酒店都快订好了。
3. 我打算十一月去成都玩一周，酒店已经订好了。

## blind-041

- Tags: fragment
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 常熬夜赶进度

**Expected Memory**

> 我在杭州做前端开发，最近连续两周都在加班赶需求。

**Top 3 Recalled**

1. 我在上海做前端开发，最近连续两周都在加班赶需求。
2. 我在杭州做前端开发，最近连续两周都在加班赶需求。
3. 我在杭州做前端开发，最近连续一个月都在加班赶需求。

## blind-042

- Tags: fragment
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 在苏州做产品这边，每周三固定周会拖到很晚才下班

**Expected Memory**

> 我在苏州做产品经理，每周三固定开周会到很晚。

**Top 3 Recalled**

1. 我在苏州做产品经理，每周三固定开周会到很晚。
2. 我在苏州做产品经理，每周四固定开周会到很晚。
3. 我在苏州做项目经理，每周三固定开周会到很晚。

## blind-043

- Tags: fragment
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 多，作息全乱了

**Expected Memory**

> 我在宁波医院做护士，这个月夜班排得特别密。

**Top 3 Recalled**

1. 我在宁波医院做护士，上个月夜班排得特别密。
2. 我在宁波医院做医生，这个月夜班排得特别密。
3. 我在宁波医院做护士，这个月夜班排得特别密。

## blind-044

- Tags: fragment
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 合肥会计月底结账那几天还要培训新人，真是经常忙到很晚

**Expected Memory**

> 我在合肥做会计，月底结账那几天经常要培训新人到很晚。

**Top 3 Recalled**

1. 我在合肥做会计，月底结账那几天经常要培训新人到很晚。
2. 我在合肥做会计，月底结账那几天经常要培训新人到六点就结束。
3. 我在合肥做出纳，月底对账那几天经常要培训新人到很晚。

## blind-045

- Tags: fragment
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 武汉幼儿园这边最近一直在改公开课教案，头大

**Expected Memory**

> 我在武汉幼儿园当老师，最近一直在改公开课教案。

**Top 3 Recalled**

1. 我在武汉幼儿园当老师，最近一直在改公开课教案。
2. 我在武汉幼儿园当老师，上个月一直在改公开课教案。
3. 我在武汉小学当老师，最近一直在改公开课教案。

## blind-046

- Tags: fragment
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 西湖跑长距离

**Expected Memory**

> 我周末常去西湖边夜跑，一次差不多十公里。

**Top 3 Recalled**

1. 我周末常去西湖边夜跑，一次差不多十公里。
2. 我周末常去西湖边夜跑，一次差不多八公里。
3. 我周末常去西湖边夜跑，一次差不多五公里。

## blind-047

- Tags: fragment
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 品胃就很难受

**Expected Memory**

> 我乳糖不耐，喝牛奶就容易肚子不舒服。

**Top 3 Recalled**

1. 我乳糖不耐，喝牛奶就容易肚子不舒服。
2. 我乳糖不耐，喝酸奶就容易肚子不舒服。
3. 我乳糖不耐，只有空腹喝牛奶才会肚子不舒服。

## blind-048

- Tags: fragment
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 雅思词汇和听力

**Expected Memory**

> 我最近在备考雅思，晚上下班后会背单词做听力。

**Top 3 Recalled**

1. 我最近在备考雅思，早上上班前会背单词做听力。
2. 我最近在备考雅思，晚上下班后会背单词但不做听力。
3. 我最近在备考雅思，晚上下班后会背单词做听力。

## blind-049

- Tags: fragment
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 我家那只橘猫叫团子，今天又拆家了，而且还是特别能吃

**Expected Memory**

> 我养了一只橘猫，名字叫团子，特别能吃。

**Top 3 Recalled**

1. 我养了一只橘猫，名字叫团子，特别能吃。
2. 我养了一只橘猫，名字叫团圆，特别能吃。
3. 我养了一只橘猫，名字叫团子，最近在控制体重吃得不多。

## blind-050

- Tags: fragment
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 但下次想试试折叠机

**Expected Memory**

> 我一直用iPhone，不过下一台手机想换折叠屏。

**Top 3 Recalled**

1. 我一直用iPhone，不过下一台手机想换折叠屏。
2. 我一直用华为，不过下一台手机想换折叠屏。
3. 我一直用iPhone，不过下一台手机想换小屏直板机。

## blind-051

- Tags: fragment
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 香菜我一口都不碰

**Expected Memory**

> 我喜欢吃重辣火锅，但是一点都不吃香菜。

**Top 3 Recalled**

1. 我喜欢吃重辣火锅，但是一点都不吃香菜。
2. 我喜欢吃微辣火锅，但是一点都不吃香菜。
3. 我喜欢吃清汤火锅，但是一点都不吃香菜。

## blind-052

- Tags: fragment
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 特别干还会起皮

**Expected Memory**

> 我皮肤偏干，换季的时候脸上很容易起皮。

**Top 3 Recalled**

1. 我皮肤偏干，夏天的时候脸上很容易起皮。
2. 我皮肤偏干，换季的时候脸上很容易起皮。
3. 我皮肤偏干，换季的时候手上很容易起皮。

## blind-053

- Tags: fragment
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 上基本不碰主食了

**Expected Memory**

> 我最近在减脂，晚饭尽量不吃米饭和面。

**Top 3 Recalled**

1. 我最近在减脂，晚饭会吃少量米饭，不再完全戒掉。
2. 我最近在减脂，晚饭尽量不吃米饭和面。
3. 我早饭一般只喝美式咖啡，不怎么吃甜的。

## blind-054

- Tags: fragment
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 啡，甜口的都不太碰

**Expected Memory**

> 我早饭一般只喝美式咖啡，不怎么吃甜的。

**Top 3 Recalled**

1. 我早饭一般只喝美式咖啡，不怎么吃甜的。
2. 我早饭一般只喝拿铁咖啡，不怎么吃甜的。
3. 我早饭一般只喝美式咖啡，特别爱吃甜的。

## blind-055

- Tags: fragment
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 了会过敏起疹子

**Expected Memory**

> 我对海鲜过敏，尤其虾蟹一吃就起疹子。

**Top 3 Recalled**

1. 我对海鲜过敏，主要是鱼类一吃就起疹子。
2. 我对海鲜过敏，尤其虾蟹一吃就起疹子。
3. 我对海鲜过敏，尤其贝类一吃就起疹子。

## blind-056

- Tags: fragment
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 本看现场演出

**Expected Memory**

> 我准备六月去日本看演唱会，机票已经在看了。

**Top 3 Recalled**

1. 我准备七月去日本看演唱会，机票已经在看了。
2. 我准备六月去日本看演唱会，机票已经在看了。
3. 我准备六月去日本看音乐节，机票已经在看了。

## blind-057

- Tags: fragment
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 上海谈事情了

**Expected Memory**

> 我每个月都要去上海出差两三次，最近尤其频繁。

**Top 3 Recalled**

1. 我每个月都要去上海出差一两次，最近尤其频繁。
2. 我每个月都要去上海出差两三次，最近尤其频繁。
3. 我每个月都要去上海出差两三次，上个月尤其频繁。

## blind-058

- Tags: fragment
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 跑着照顾妈妈

**Expected Memory**

> 我妈妈最近住院了，我白天要来回照顾她。

**Top 3 Recalled**

1. 我妈妈最近住院了，我白天要来回照顾她。
2. 我妈妈最近在家休养，我白天要来回照顾她。
3. 我妈妈最近住院了，我晚上要过去陪护她。

## blind-059

- Tags: fragment
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 准备教资考试

**Expected Memory**

> 我准备十二月考教师资格证，周末都在刷题。

**Top 3 Recalled**

1. 我准备十二月考教师资格证，周末都在刷题。
2. 我准备十二月考教师资格证，最近报了辅导班每天上课。
3. 我准备十一月考教师资格证，周末都在刷题。

## blind-060

- Tags: fragment
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 待几天放松一下

**Expected Memory**

> 我打算十一月去成都玩一周，酒店都快订好了。

**Top 3 Recalled**

1. 我打算十一月去成都玩三天，酒店都快订好了。
2. 我打算十一月去重庆玩一周，酒店都快订好了。
3. 我打算十一月去成都玩一周，酒店都快订好了。

## blind-061

- Tags: typo, spoken, fragment, mixed_noise
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就常熬页赶进度那种

**Expected Memory**

> 我在杭州做前端开发，最近连续两周都在加班赶需求。

**Top 3 Recalled**

1. 我在杭州做前端开发，最近连续一个月都在加班赶需求。
2. 我在上海做前端开发，最近连续两周都在加班赶需求。
3. 我在杭州做前端开发，最近连续两周都在加班赶需求。

## blind-062

- Tags: typo, spoken, fragment, mixed_noise
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 就苏州做产品那种，礼拜三周会拖到很晚才下般

**Expected Memory**

> 我在苏州做产品经理，每周三固定开周会到很晚。

**Top 3 Recalled**

1. 我在苏州做产品经理，每周三固定开周会到很晚。
2. 我在苏州做产品经理，每周四固定开周会到很晚。
3. 我在苏州做产品经理，每周三固定开评审会到很晚。

## blind-063

- Tags: typo, spoken, fragment, mixed_noise
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就宁波医院这月夜班特多那种，我做护士作息全乱了

**Expected Memory**

> 我在宁波医院做护士，这个月夜班排得特别密。

**Top 3 Recalled**

1. 我在宁波医院做护士，上个月夜班排得特别密。
2. 我在宁波医院做护士，这个月夜班排得特别密。
3. 我在宁波医院做医生，这个月夜班排得特别密。

## blind-064

- Tags: typo, spoken, fragment, mixed_noise
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就做账，经常忙到很晚那种

**Expected Memory**

> 我在合肥做会计，月底结账那几天经常要培训新人到很晚。

**Top 3 Recalled**

1. 我在合肥做会计，月底结账那几天经常要加班对账到很晚。
2. 我在南京做会计，月底结账那几天经常要培训新人到很晚。
3. 我在合肥做会计，月底结账那几天经常要培训新人到很晚。

## blind-065

- Tags: typo, spoken, fragment, mixed_noise
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 就武汉幼儿园最近一直在改公开刻教案那种

**Expected Memory**

> 我在武汉幼儿园当老师，最近一直在改公开课教案。

**Top 3 Recalled**

1. 我在武汉幼儿园当老师，最近一直在改公开课教案。
2. 我在武汉幼儿园当老师，上个月一直在改公开课教案。
3. 我在武汉小学当老师，最近一直在改公开课教案。

## blind-066

- Tags: typo, spoken, fragment, mixed_noise
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就西湖炮长距离那种

**Expected Memory**

> 我周末常去西湖边夜跑，一次差不多十公里。

**Top 3 Recalled**

1. 我周末常去西湖边夜跑，一次差不多五公里。
2. 我周末常去西湖边夜跑，一次差不多十公里。
3. 我周末常去西湖边夜跑，一次差不多八公里。

## blind-067

- Tags: typo, spoken, fragment, mixed_noise
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就品胃就很难受那种

**Expected Memory**

> 我乳糖不耐，喝牛奶就容易肚子不舒服。

**Top 3 Recalled**

1. 我乳糖不耐，喝酸奶就容易肚子不舒服。
2. 我乳糖不耐，喝牛奶就容易肚子不舒服。
3. 我乳糖不耐，只有空腹喝牛奶才会肚子不舒服。

## blind-068

- Tags: typo, spoken, fragment, mixed_noise
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就在刷雅思词汇和听力那种

**Expected Memory**

> 我最近在备考雅思，晚上下班后会背单词做听力。

**Top 3 Recalled**

1. 我最近在备考雅思，早上上班前会背单词做听力。
2. 我最近在备考雅思，晚上下班后会背单词做听力。
3. 我最近在备考雅思，晚上下班后会刷口语题不怎么做听力。

## blind-069

- Tags: typo, spoken, fragment, mixed_noise
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 就那只橘猫团子又拆家还特别能吃那种

**Expected Memory**

> 我养了一只橘猫，名字叫团子，特别能吃。

**Top 3 Recalled**

1. 我养了一只橘猫，名字叫团子，特别能吃。
2. 我养了一只橘猫，名字叫团圆，特别能吃。
3. 我养了一只橘猫，名字叫团子，但它其实很挑食。

## blind-070

- Tags: typo, spoken, fragment, mixed_noise
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 就机，但下次想试试折叠机那种

**Expected Memory**

> 我一直用iPhone，不过下一台手机想换折叠屏。

**Top 3 Recalled**

1. 我一直用iPhone，不过下一台手机想换折叠屏。
2. 我一直用华为，不过下一台手机想换折叠屏。
3. 我一直用iPhone，不过下一台手机想换小屏直板机。

## blind-071

- Tags: typo, spoken, fragment, mixed_noise
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 就凡是香菜我一口都不碰那种

**Expected Memory**

> 我喜欢吃重辣火锅，但是一点都不吃香菜。

**Top 3 Recalled**

1. 我喜欢吃重辣火锅，但是一点都不吃香菜。
2. 我喜欢吃微辣火锅，但是一点都不吃香菜。
3. 我喜欢吃清汤火锅，但是一点都不吃香菜。

## blind-072

- Tags: typo, spoken, fragment, mixed_noise
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 就特别干还汇起皮那种

**Expected Memory**

> 我皮肤偏干，换季的时候脸上很容易起皮。

**Top 3 Recalled**

1. 我皮肤偏干，换季的时候脸上很容易起皮。
2. 我皮肤偏干，夏天的时候脸上很容易起皮。
3. 我皮肤偏干，换季的时候手上很容易起皮。

## blind-073

- Tags: typo, spoken, fragment, mixed_noise
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 就，晚上基本不碰主食了那种

**Expected Memory**

> 我最近在减脂，晚饭尽量不吃米饭和面。

**Top 3 Recalled**

1. 我最近在减脂，晚饭尽量不吃米饭和面。
2. 我最近在减脂，晚饭尽量不吃油炸和甜食。
3. 我最近在减脂，晚饭会吃少量米饭，不再完全戒掉。

## blind-074

- Tags: typo, spoken, fragment, mixed_noise
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 就黑咖啡，甜口的都不太碰那种

**Expected Memory**

> 我早饭一般只喝美式咖啡，不怎么吃甜的。

**Top 3 Recalled**

1. 我早饭一般只喝美式咖啡，不怎么吃甜的。
2. 我早饭一般只喝拿铁咖啡，不怎么吃甜的。
3. 我早饭一般只喝美式咖啡，特别爱吃甜的。

## blind-075

- Tags: typo, spoken, fragment, mixed_noise
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就了汇过敏起疹子那种

**Expected Memory**

> 我对海鲜过敏，尤其虾蟹一吃就起疹子。

**Top 3 Recalled**

1. 我对海鲜过敏，主要是鱼类一吃就起疹子。
2. 我对海鲜过敏，尤其贝类一吃就起疹子。
3. 我对海鲜过敏，尤其虾蟹一吃就起疹子。

## blind-076

- Tags: typo, spoken, fragment, mixed_noise
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 就六月想去日本看现场演楚那种，机票还在看

**Expected Memory**

> 我准备六月去日本看演唱会，机票已经在看了。

**Top 3 Recalled**

1. 我准备六月去日本看演唱会，机票已经在看了。
2. 我准备六月去日本看音乐节，机票已经在看了。
3. 我准备六月去日本看演唱会，机票已经买好了。

## blind-077

- Tags: typo, spoken, fragment, mixed_noise
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就每个月都得去上孩出差两三次谈事情，最近尤其频繁那种

**Expected Memory**

> 我每个月都要去上海出差两三次，最近尤其频繁。

**Top 3 Recalled**

1. 我每个月都要去上海出差两三次，上个月尤其频繁。
2. 我每个月都要去上海出差两三次，最近尤其频繁。
3. 我每个月都要去上海出差一两次，最近尤其频繁。

## blind-078

- Tags: typo, spoken, fragment, mixed_noise
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 就妈妈住院了我白天得来回跑着照顾她那种

**Expected Memory**

> 我妈妈最近住院了，我白天要来回照顾她。

**Top 3 Recalled**

1. 我妈妈最近住院了，我白天要来回照顾她。
2. 我妈妈最近住院了，我白天主要去医院帮她办理检查。
3. 我妈妈最近在家休养，我白天要来回照顾她。

## blind-079

- Tags: typo, spoken, fragment, mixed_noise
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 就都在准备教资考试那种

**Expected Memory**

> 我准备十二月考教师资格证，周末都在刷题。

**Top 3 Recalled**

1. 我准备十二月考教师资格证，周末都在刷题。
2. 我准备十一月考教师资格证，周末都在刷题。
3. 我准备十二月考教师资格证，最近报了辅导班每天上课。

## blind-080

- Tags: typo, spoken, fragment, mixed_noise
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 就成都待几天放松一下那种

**Expected Memory**

> 我打算十一月去成都玩一周，酒店都快订好了。

**Top 3 Recalled**

1. 我打算十一月去成都玩一周，打算住民宿不订酒店。
2. 我打算十一月去成都玩一周，酒店都快订好了。
3. 我打算十一月去成都玩三天，酒店都快订好了。

## blind-081

- Tags: distractor
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 反正最近写页面经常熬夜赶进度，这事最近还挺频繁

**Expected Memory**

> 我在杭州做前端开发，最近连续两周都在加班赶需求。

**Top 3 Recalled**

1. 我在上海做前端开发，最近连续两周都在加班赶需求。
2. 我在杭州做前端开发，最近连续两周都在加班赶需求。
3. 我在杭州做前端开发，最近连续一个月都在加班赶需求。

## blind-082

- Tags: distractor
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 反正礼拜三总是开会拖到很晚才下班，这事最近还挺频繁

**Expected Memory**

> 我在苏州做产品经理，每周三固定开周会到很晚。

**Top 3 Recalled**

1. 我在苏州做项目经理，每周三固定开周会到很晚。
2. 我在上海做产品经理，每周三固定开周会到很晚。
3. 我在苏州做产品经理，每周三固定开周会到很晚。

## blind-083

- Tags: distractor
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 反正我在宁波医院做护士，这个月夜班排得真密，作息全乱了，这事最近还挺频繁

**Expected Memory**

> 我在宁波医院做护士，这个月夜班排得特别密。

**Top 3 Recalled**

1. 我在宁波医院做护士，这个月夜班排得特别密。
2. 我在宁波医院做护士，上个月夜班排得特别密。
3. 我在宁波医院做医生，这个月夜班排得特别密。

## blind-084

- Tags: distractor
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 反正月底带新人做账，经常忙到很晚，这事最近还挺频繁

**Expected Memory**

> 我在合肥做会计，月底结账那几天经常要培训新人到很晚。

**Top 3 Recalled**

1. 我在南京做会计，月底结账那几天经常要培训新人到很晚。
2. 我在合肥做会计，月底结账那几天经常要培训新人到很晚。
3. 我在合肥做出纳，月底对账那几天经常要培训新人到很晚。

## blind-085

- Tags: distractor
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 反正我在武汉幼儿园当老师，最近一直在改公开课教案，这事最近还挺频繁

**Expected Memory**

> 我在武汉幼儿园当老师，最近一直在改公开课教案。

**Top 3 Recalled**

1. 我在武汉幼儿园当老师，上个月一直在改公开课教案。
2. 我在武汉幼儿园当老师，最近一直在改公开课教案。
3. 我在武汉小学当老师，最近一直在改公开课教案。

## blind-086

- Tags: distractor
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 反正休息天会绕着西湖跑长距离，这事最近还挺频繁

**Expected Memory**

> 我周末常去西湖边夜跑，一次差不多十公里。

**Top 3 Recalled**

1. 我工作日下班后会去西湖夜跑，一次差不多十公里。
2. 我周末常去西湖边夜跑，一次差不多十公里。
3. 我周末常去西湖边晨跑，一次差不多十公里。

## blind-087

- Tags: distractor
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 反正一喝奶制品胃就很难受，这事最近还挺频繁

**Expected Memory**

> 我乳糖不耐，喝牛奶就容易肚子不舒服。

**Top 3 Recalled**

1. 我乳糖不耐，喝牛奶就容易肚子不舒服。
2. 我乳糖不耐，喝奶茶比喝纯牛奶更容易不舒服。
3. 我乳糖不耐，喝酸奶就容易肚子不舒服。

## blind-088

- Tags: distractor
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 反正晚上基本都在刷雅思词汇和听力，这事最近还挺频繁

**Expected Memory**

> 我最近在备考雅思，晚上下班后会背单词做听力。

**Top 3 Recalled**

1. 我最近在备考雅思，晚上下班后会背单词做听力。
2. 我最近在备考雅思，晚上下班后会刷口语题不怎么做听力。
3. 我最近在备考雅思，晚上下班后主要做阅读和写作。

## blind-089

- Tags: distractor
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 反正家里那只叫团子的橘猫今天又拆家了，这事最近还挺频繁

**Expected Memory**

> 我养了一只橘猫，名字叫团子，特别能吃。

**Top 3 Recalled**

1. 我养了一只橘猫，名字叫团子，最近在控制体重吃得不多。
2. 我养了一只橘猫，名字叫团子，特别能吃。
3. 我养了一只橘猫，名字叫团子，但它其实很挑食。

## blind-090

- Tags: distractor
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 反正虽然一直拿苹果手机，但下次想试试折叠机，这事最近还挺频繁

**Expected Memory**

> 我一直用iPhone，不过下一台手机想换折叠屏。

**Top 3 Recalled**

1. 我一直用iPhone，不过下一台手机想换折叠屏。
2. 我一直用华为，不过下一台手机想换折叠屏。
3. 我一直用iPhone，不过下一台手机想换游戏手机。

## blind-091

- Tags: distractor
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 反正辣锅可以，但凡是香菜我一口都不碰，这事最近还挺频繁

**Expected Memory**

> 我喜欢吃重辣火锅，但是一点都不吃香菜。

**Top 3 Recalled**

1. 我喜欢吃麻辣烫，口味要重辣，但香菜我不吃。
2. 我喜欢吃微辣火锅，但是一点都不吃香菜。
3. 我喜欢吃重辣火锅，但是一点都不吃香菜。

## blind-092

- Tags: distractor
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 反正一到换季脸上就特别干还会起皮，这事最近还挺频繁

**Expected Memory**

> 我皮肤偏干，换季的时候脸上很容易起皮。

**Top 3 Recalled**

1. 我皮肤偏干，换季的时候脸上很容易起皮。
2. 我皮肤偏干，换季的时候脸上很容易泛红不太起皮。
3. 我皮肤偏干，换季的时候主要是嘴角起皮。

## blind-093

- Tags: distractor
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 反正最近控制体重，晚上基本不碰主食了，这事最近还挺频繁

**Expected Memory**

> 我最近在减脂，晚饭尽量不吃米饭和面。

**Top 3 Recalled**

1. 我最近在减脂，晚饭尽量不吃油炸和甜食。
2. 我最近在减脂，晚饭尽量不吃米饭和面。
3. 我最近在减脂，晚饭尽量不吃米饭和面，改成吃燕麦。

## blind-094

- Tags: distractor
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 反正早上通常就一杯黑咖啡，甜口的都不太碰，这事最近还挺频繁

**Expected Memory**

> 我早饭一般只喝美式咖啡，不怎么吃甜的。

**Top 3 Recalled**

1. 我早饭一般只喝拿铁咖啡，不怎么吃甜的。
2. 我早饭一般只喝美式咖啡，不怎么吃甜的。
3. 我早饭一般只喝美式咖啡，偶尔会加糖和奶。

## blind-095

- Tags: distractor
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 反正虾蟹这种海鲜我吃了会过敏起疹子，这事最近还挺频繁

**Expected Memory**

> 我对海鲜过敏，尤其虾蟹一吃就起疹子。

**Top 3 Recalled**

1. 我对海鲜过敏，尤其虾蟹一吃就起疹子。
2. 我对海鲜过敏，虾还能吃一点，螃蟹一吃就起疹子。
3. 我对海鲜过敏，去年吃虾蟹才起疹子。

## blind-096

- Tags: distractor
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 反正六月想飞去日本看现场演出，这事最近还挺频繁

**Expected Memory**

> 我准备六月去日本看演唱会，机票已经在看了。

**Top 3 Recalled**

1. 我准备六月去日本看演唱会，机票已经在看了。
2. 我准备六月去日本看音乐节，机票已经在看了。
3. 我准备六月去日本看演唱会，机票已经买好了。

## blind-097

- Tags: distractor
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 反正这个月又得跑上海谈事情了，这事最近还挺频繁

**Expected Memory**

> 我每个月都要去上海出差两三次，最近尤其频繁。

**Top 3 Recalled**

1. 我每个月都要去上海出差一两次，最近尤其频繁。
2. 我每个月都要去上海出差两三次，最近尤其频繁。
3. 我每个月都要去上海出差两三次，上个月尤其频繁。

## blind-098

- Tags: distractor
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 反正白天还得往医院跑着照顾妈妈，这事最近还挺频繁

**Expected Memory**

> 我妈妈最近住院了，我白天要来回照顾她。

**Top 3 Recalled**

1. 我妈妈最近住院了，我白天要来回照顾她。
2. 我妈妈最近住院了，我白天主要去医院帮她办理检查。
3. 我妈妈最近在家休养，我白天要来回照顾她。

## blind-099

- Tags: distractor
- Top1 Hit: NO
- Top3 Hit: YES

**Query**

> 反正休息天基本都在准备教资考试，这事最近还挺频繁

**Expected Memory**

> 我准备十二月考教师资格证，周末都在刷题。

**Top 3 Recalled**

1. 我准备十二月考教师资格证，平时晚上复习，周末反而休息。
2. 我准备十二月考教师资格证，周末都在刷题。
3. 我准备十一月考教师资格证，周末都在刷题。

## blind-100

- Tags: distractor
- Top1 Hit: YES
- Top3 Hit: YES

**Query**

> 反正十一月想去成都待几天放松一下，这事最近还挺频繁

**Expected Memory**

> 我打算十一月去成都玩一周，酒店都快订好了。

**Top 3 Recalled**

1. 我打算十一月去成都玩一周，酒店都快订好了。
2. 我打算十一月去成都玩三天，酒店都快订好了。
3. 我打算十一月去成都玩一周，机票都快订好了。
