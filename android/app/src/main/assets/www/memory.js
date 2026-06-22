// ======================
// 双模式兼容版：登录用户 + 匿名用户 都有历史记录
// 使用本地存储替代后端API（Android WebView版本）
// ======================

// 初始化：匿名用户自动生成唯一ID（本地永久存储）
function initAnonymousId() {
    let anonId = localStorage.getItem("anonymous_id");
    if (!anonId) {
        const timestamp = Date.now().toString();
        const randomStr = Math.random().toString(36).substr(2, 8);
        anonId = "anon_" + timestamp + "_" + randomStr;
        anonId = anonId.substring(0, 50);
        localStorage.setItem("anonymous_id", anonId);
    }
    return anonId;
}

// 获取当前用户ID
function getUserId() {
    const token = localStorage.getItem("token");
    if (token) {
        return 'user_' + token.substring(0, 16);
    }
    return initAnonymousId();
}

// 对外接口（使用本地存储）
window.memoryManager = {
    async saveRecord(record) {
        try {
            const result = window.localStorageManager.saveRecord(record);
            return result;
        } catch (e) {
            console.error("保存记录失败：", e);
            return { code: 500, msg: "保存失败" };
        }
    },
    async getRecords() {
        try {
            const records = window.localStorageManager.getRecords();
            // 只返回当前用户的记录
            const userId = getUserId();
            return records.filter(r => r.userId === userId);
        } catch (e) {
            console.error("获取记录失败：", e);
            return [];
        }
    },
    async getRecordDetail(id) {
        try {
            const result = window.localStorageManager.getRecordDetail(id);
            return result;
        } catch (e) {
            console.error("获取记录详情失败：", e);
            return { code: 500, msg: "获取失败" };
        }
    },
    async deleteRecord(id) {
        try {
            const result = window.localStorageManager.deleteRecord(id);
            return result;
        } catch (e) {
            console.error("删除记录失败：", e);
            return { code: 500, msg: "删除失败" };
        }
    },
    async clearAllRecords() {
        try {
            const result = window.localStorageManager.clearAllRecords();
            return result;
        } catch (e) {
            console.error("清空记录失败：", e);
            return { code: 500, msg: "清空失败" };
        }
    },
    async compareRecords(ids) {
        try {
            const result = window.localStorageManager.compareRecords(ids);
            return result;
        } catch (e) {
            console.error("比较记录失败：", e);
            return { code: 500, msg: "比较失败" };
        }
    }
};
