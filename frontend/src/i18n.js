export const messages = {
  zh: {
    common: {
      unknownUser: "未知用户",
      close: "关闭",
      save: "保存",
      saving: "保存中...",
      reset: "重置",
      settings: "设置",
      comments: "评论",
      gifts: "礼物",
      totalGifts: "总礼物数",
      totalDiamonds: "总钻石数",
      firstSeen: "首次出现",
      lastSeen: "最近出现",
      lastComment: "最近评论",
      lastGift: "最近礼物",
      noData: "暂无数据",
      yes: "是",
      no: "否",
      notAvailable: "暂无",
      edit: "编辑",
      delete: "删除",
      pinned: "置顶",
    },
    status: {
      room: "房间",
      roomPlaceholder: "输入房间号",
      noRoomSelected: "未选择房间",
      switchRoom: "切换房间",
      switching: "切换中...",
      connection: "连接",
      model: "模型",
      totalEvents: "总事件数",
      connectionState: {
        idle: "未连接",
        connecting: "连接中",
        live: "已连接",
        reconnecting: "重连中",
        switching: "切换中",
      },
      modelResult: {
        idle: "空闲",
        ok: "正常",
        fallback: "降级",
        llm_generation_failed: "生成失败",
      },
      modelMode: {
        heuristic: "规则",
        model: "模型",
        local: "本地",
      },
    },
    theme: {
      switchToLight: "切换浅色主题",
      switchToDark: "切换深色主题",
    },
    teleprompter: {
      badge: "提词器",
      title: "当前优先展示的回复建议",
      sourceContent: "原始内容",
      suggestionReply: "建议回复",
      waiting: "等待新的弹幕与建议...",
      source: {
        model: "模型生成",
        heuristic: "规则生成",
        heuristic_fallback: "规则兜底",
      },
    },
    feed: {
      title: "实时消息流",
      clear: "清空",
      showAll: "显示全部",
      showing: "当前显示 {selected} / {total} 类事件",
      user: "用户",
      content: "内容",
      empty: "当前筛选下没有消息。",
      eventType: {
        comment: "弹幕",
        gift: "礼物",
        follow: "关注",
        member: "进场",
        like: "点赞",
        system: "系统",
      },
      processing: {
        persisted: "\u5df2\u843d\u5e93",
        notPersisted: "\u672a\u843d\u5e93",
        memorySaved: "\u5df2\u4fdd\u5b58\u8bb0\u5fc6",
        noMemorySaved: "\u672a\u4ea7\u51fa\u8bb0\u5fc6",
        memoryRecalled: "\u547d\u4e2d\u53ec\u56de",
        noMemoryRecalled: "\u672a\u547d\u4e2d\u53ec\u56de",
        suggestionGenerated: "\u5df2\u751f\u6210\u63d0\u8bcd",
        noSuggestionGenerated: "\u672a\u751f\u6210\u63d0\u8bcd",
        showDetails: "\u67e5\u770b\u8be6\u60c5",
        hideDetails: "\u6536\u8d77\u8be6\u60c5",
        savedMemoryIds: "\u4fdd\u5b58\u8bb0\u5fc6 ID",
        recalledMemoryIds: "\u53ec\u56de\u8bb0\u5fc6 ID",
        suggestionId: "\u63d0\u8bcd ID",
      },
    },
    viewerWorkbench: {
      title: "观众工作台",
      loading: "正在加载观众详情...",
      selectHint: "点击事件流中的观众查看详情。",
      memories: "语义记忆",
      noMemories: "还没有记忆数据。",
      notes: "备注",
      notePlaceholder: "写一条备注...",
      pinNote: "置顶备注",
      unpinNote: "取消置顶",
      updateNote: "更新备注",
      saveNote: "保存备注",
      editing: "正在编辑",
      noNotes: "还没有备注。",
      notesNeedViewerId: "备注功能需要可用的 viewer id。",
      recentComments: "最近评论",
      noRecentComments: "暂无最近评论。",
      recentGiftEvents: "最近送礼",
      noRecentGiftEvents: "暂无最近送礼。",
      recentSessions: "最近场次",
      noRecentSessions: "暂无最近场次。",
      emptyContent: "(空内容)",
      memoryType: "类型",
      memoryConfidence: "置信度",
      memoryRecall: "召回次数",
      sessionSummary: "场次 {sessionId} / 评论 {comments} / 礼物 {gifts}",
    },
    llmSettings: {
      title: "模型设置",
      subtitle: "保存到 SQLite，后续新提词会立刻使用。",
      model: "模型名",
      modelDefault: "默认值：{value}",
      systemPrompt: "系统提示词",
      promptHint: "重置会回到后端默认提示词。",
    },
    locale: {
      switchToEnglish: "EN",
      switchToChinese: "中文",
    },
    errors: {
      roomRequired: "请输入房间号",
      roomSwitchFailed: "切换房间失败",
      llmSettingsLoadFailed: "加载模型设置失败",
      llmSettingsSaveFailed: "保存模型设置失败",
      viewerLoadFailed: "加载观众详情失败",
      viewerNoteSaveFailed: "保存备注失败",
      viewerNoteDeleteFailed: "删除备注失败",
      viewerNoteRequired: "备注内容不能为空",
      viewerIdRequiredToSaveNotes: "保存备注需要可用的 viewer id",
      viewerIdRequiredToDeleteNotes: "删除备注需要可用的 viewer id",
    },
  },
  en: {
    common: {
      unknownUser: "Unknown user",
      close: "Close",
      save: "Save",
      saving: "Saving...",
      reset: "Reset",
      settings: "Settings",
      comments: "Comments",
      gifts: "Gifts",
      totalGifts: "Total gifts",
      totalDiamonds: "Total diamonds",
      firstSeen: "First seen",
      lastSeen: "Last seen",
      lastComment: "Last comment",
      lastGift: "Last gift",
      noData: "No data",
      yes: "Yes",
      no: "No",
      notAvailable: "N/A",
      edit: "Edit",
      delete: "Delete",
      pinned: "Pinned",
    },
    status: {
      room: "Room",
      roomPlaceholder: "Enter room id",
      noRoomSelected: "No room selected",
      switchRoom: "Switch Room",
      switching: "Switching...",
      connection: "Connection",
      model: "Model",
      totalEvents: "Total Events",
      connectionState: {
        idle: "Idle",
        connecting: "Connecting",
        live: "Live",
        reconnecting: "Reconnecting",
        switching: "Switching",
      },
      modelResult: {
        idle: "Idle",
        ok: "OK",
        fallback: "Fallback",
        llm_generation_failed: "Generation Failed",
      },
      modelMode: {
        heuristic: "Heuristic",
        model: "Model",
        local: "Local",
      },
    },
    theme: {
      switchToLight: "Switch to light theme",
      switchToDark: "Switch to dark theme",
    },
    teleprompter: {
      badge: "Teleprompter",
      title: "Highest-priority reply suggestion",
      sourceContent: "Source Content",
      suggestionReply: "Suggested Reply",
      waiting: "Waiting for the next live comment and suggestion...",
      source: {
        model: "Model",
        heuristic: "Heuristic",
        heuristic_fallback: "Fallback",
      },
    },
    feed: {
      title: "Live Feed",
      clear: "Clear",
      showAll: "Show All",
      showing: "Showing {selected} / {total} event types",
      user: "User",
      content: "Content",
      empty: "No events match the current filters.",
      eventType: {
        comment: "Comment",
        gift: "Gift",
        follow: "Follow",
        member: "Join",
        like: "Like",
        system: "System",
      },
      processing: {
        persisted: "Persisted",
        notPersisted: "Not Persisted",
        memorySaved: "Memory Saved",
        noMemorySaved: "No Memory Saved",
        memoryRecalled: "Recall Hit",
        noMemoryRecalled: "No Recall Hit",
        suggestionGenerated: "Suggestion Generated",
        noSuggestionGenerated: "No Suggestion",
        showDetails: "Show Details",
        hideDetails: "Hide Details",
        savedMemoryIds: "Saved Memory IDs",
        recalledMemoryIds: "Recalled Memory IDs",
        suggestionId: "Suggestion ID",
      },
    },
    viewerWorkbench: {
      title: "Viewer Workbench",
      loading: "Loading viewer details...",
      selectHint: "Select a viewer from the live feed to inspect details.",
      memories: "Memories",
      noMemories: "No memories recorded yet.",
      notes: "Notes",
      notePlaceholder: "Write a note...",
      pinNote: "Pin note",
      unpinNote: "Unpin note",
      updateNote: "Update note",
      saveNote: "Save note",
      editing: "Editing",
      noNotes: "No notes yet.",
      notesNeedViewerId: "Notes require a resolved viewer id.",
      recentComments: "Recent Comments",
      noRecentComments: "No recent comments.",
      recentGiftEvents: "Recent Gift Events",
      noRecentGiftEvents: "No recent gift events.",
      recentSessions: "Recent Sessions",
      noRecentSessions: "No recent sessions.",
      emptyContent: "(empty)",
      memoryType: "Type",
      memoryConfidence: "Confidence",
      memoryRecall: "Recall",
      sessionSummary: "Session {sessionId} / comments {comments} / gifts {gifts}",
    },
    llmSettings: {
      title: "LLM Settings",
      subtitle: "Persisted in SQLite and applied to future suggestions.",
      model: "Model",
      modelDefault: "Default: {value}",
      systemPrompt: "System Prompt",
      promptHint: "Reset restores the backend default prompt.",
    },
    locale: {
      switchToEnglish: "EN",
      switchToChinese: "中文",
    },
    errors: {
      roomRequired: "Please enter a room id",
      roomSwitchFailed: "Failed to switch room",
      llmSettingsLoadFailed: "Failed to load LLM settings",
      llmSettingsSaveFailed: "Failed to save LLM settings",
      viewerLoadFailed: "Failed to load viewer details",
      viewerNoteSaveFailed: "Failed to save viewer note",
      viewerNoteDeleteFailed: "Failed to delete viewer note",
      viewerNoteRequired: "Note content is required",
      viewerIdRequiredToSaveNotes: "Viewer id is required to save notes",
      viewerIdRequiredToDeleteNotes: "Viewer id is required to delete notes",
    },
  },
};

export function translate(locale, key, params = {}) {
  const dictionary = messages[locale] || messages.zh;
  const fallback = messages.zh;
  const path = key.split(".");

  let value = dictionary;
  for (const segment of path) {
    value = value?.[segment];
  }

  if (typeof value !== "string") {
    value = fallback;
    for (const segment of path) {
      value = value?.[segment];
    }
  }

  if (typeof value !== "string") {
    return key;
  }

  return Object.entries(params).reduce(
    (text, [name, replacement]) => text.replaceAll(`{${name}}`, `${replacement}`),
    value,
  );
}

export function translateError(locale, value) {
  if (typeof value !== "string" || !value) {
    return "";
  }

  if (value.startsWith("errors.")) {
    return translate(locale, value);
  }

  return value;
}
