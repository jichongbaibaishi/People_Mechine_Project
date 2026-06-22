// ======================
// 本地存储管理器 - 替代后端记录API
// 使用 localStorage 存储所有数据
// ======================

(function() {
    'use strict';

    const STORAGE_KEY = 'stress_assessment_records';
    const USER_KEY = 'stress_assessment_user';
    const CHAT_KEY = 'stress_assessment_chat';

    // 初始化匿名ID
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

    // 获取当前用户信息
    function getCurrentUser() {
        const token = localStorage.getItem("token");
        const userStr = localStorage.getItem(USER_KEY);
        if (token && userStr) {
            try {
                return JSON.parse(userStr);
            } catch (e) {
                return null;
            }
        }
        return { id: initAnonymousId(), isAnonymous: true };
    }

    // 获取所有记录
    function getRecords() {
        try {
            const data = localStorage.getItem(STORAGE_KEY);
            return data ? JSON.parse(data) : [];
        } catch (e) {
            return [];
        }
    }

    // 保存记录
    function saveRecord(record) {
        const records = getRecords();
        const newRecord = {
            id: 'record_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9),
            ...record,
            userId: getCurrentUser().id,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
        };
        records.push(newRecord);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
        return { code: 200, msg: "保存成功", data: newRecord };
    }

    // 获取记录详情
    function getRecordDetail(id) {
        const records = getRecords();
        const record = records.find(r => r.id === id);
        if (record) {
            return { code: 200, msg: "success", data: record };
        }
        return { code: 404, msg: "记录不存在" };
    }

    // 删除记录
    function deleteRecord(id) {
        let records = getRecords();
        records = records.filter(r => r.id !== id);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
        return { code: 200, msg: "删除成功" };
    }

    // 清空所有记录
    function clearAllRecords() {
        localStorage.setItem(STORAGE_KEY, JSON.stringify([]));
        return { code: 200, msg: "已清空所有记录" };
    }

    // 比较记录
    function compareRecords(ids) {
        const records = getRecords();
        const result = records.filter(r => ids.includes(r.id));
        return { code: 200, msg: "success", data: result };
    }

    // 获取最新记录
    function getLatestRecords(limit) {
        const records = getRecords();
        limit = limit || 10;
        return records.slice(-limit).reverse();
    }

    // 获取压力趋势数据
    function getStressTrend() {
        const records = getRecords();
        return records.map(r => ({
            id: r.id,
            date: r.createdAt,
            stressLevel: r.stressLevel || r.result?.score || 0,
            scenarioType: r.scenarioType || 'unknown'
        }));
    }

    // 聊天历史管理
    function saveChatMessage(message) {
        let chats = [];
        try {
            const data = localStorage.getItem(CHAT_KEY);
            chats = data ? JSON.parse(data) : [];
        } catch (e) {}
        chats.push({
            ...message,
            timestamp: new Date().toISOString()
        });
        localStorage.setItem(CHAT_KEY, JSON.stringify(chats));
        return chats;
    }

    function getChatHistory() {
        try {
            const data = localStorage.getItem(CHAT_KEY);
            return data ? JSON.parse(data) : [];
        } catch (e) {
            return [];
        }
    }

    function clearChatHistory() {
        localStorage.setItem(CHAT_KEY, JSON.stringify([]));
        return { code: 200, msg: "聊天历史已清空" };
    }

    // 用户登录/注册（本地模拟）
    function login(username, password) {
        const user = {
            id: 'user_' + username + '_' + Date.now(),
            username: username,
            token: 'token_' + Math.random().toString(36).substr(2, 20),
            createdAt: new Date().toISOString()
        };
        localStorage.setItem("token", user.token);
        localStorage.setItem(USER_KEY, JSON.stringify(user));
        return { code: 200, msg: "登录成功", data: user };
    }

    function register(username, password) {
        return login(username, password);
    }

    function logout() {
        localStorage.removeItem("token");
        localStorage.removeItem(USER_KEY);
        return { code: 200, msg: "已退出登录" };
    }

    function getUserInfo() {
        const user = getCurrentUser();
        return { code: 200, msg: "success", data: user };
    }

    // 公开API
    window.localStorageManager = {
        saveRecord: saveRecord,
        getRecords: getRecords,
        getRecordDetail: getRecordDetail,
        deleteRecord: deleteRecord,
        clearAllRecords: clearAllRecords,
        compareRecords: compareRecords,
        getLatestRecords: getLatestRecords,
        getStressTrend: getStressTrend,
        saveChatMessage: saveChatMessage,
        getChatHistory: getChatHistory,
        clearChatHistory: clearChatHistory,
        login: login,
        register: register,
        logout: logout,
        getUserInfo: getUserInfo,
        getCurrentUser: getCurrentUser,
        initAnonymousId: initAnonymousId
    };

    console.log('Local Storage Manager initialized successfully');
})();
