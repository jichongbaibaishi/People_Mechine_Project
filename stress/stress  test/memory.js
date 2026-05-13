// ======================
// 双模式兼容版：登录用户 + 匿名用户 都有历史记录
// ======================
const BASE_URL = "http://127.0.0.1:8000/api/record";

// 初始化：匿名用户自动生成唯一ID（本地永久存储）
function initAnonymousId() {
    let anonId = localStorage.getItem("anonymous_id");
    if (!anonId) {
        // 缩短随机串长度，确保整体不超过50字符（后端 anonymous_id 字段是 String(50)）
        const timestamp = Date.now().toString();
        const randomStr = Math.random().toString(36).substr(2, 8);
        anonId
= "anon_" + timestamp + "_" + randomStr;
        // 兜底截断，防止超长
        anonId
= anonId.substring(0, 50);
        localStorage.setItem("anonymous_id", anonId);
    }
    return anonId;
}
// 获取请求头（自动携带Token/匿名ID）
function getHeaders() {
    const headers = { "Content-Type": "application/json" };
    const token = localStorage.getItem("token");
    if (token) {
        headers["Authorization"] = "Bearer " + token;
    } else {
        headers["Anonymous-ID"] = initAnonymousId();
    }
    return headers;
}

// 统一请求
async function request(url, method = "GET", body = null) {
    const headers = getHeaders();
    console.log("请求头信息：", headers); // 打印到控制台，检查是否有 Anonymous-ID
    const options = { method, headers };
    if (body) options.body = JSON.stringify(body);

    try {
        const res = await fetch(BASE_URL + url, options);
        return await res.json();
    } catch (e) {
        console.error("请求失败：", e);
        return { code: 500, msg: "网络异常" };
    }
}
// 对外接口（完全兼容原有调用）
window.memoryManager = {
    async saveRecord(record) {
        return await request("/save", "POST", record);
    },
    async getRecords() {
        const res = await request("/list");
        return res.data || [];
    },
    async getRecordDetail(id) {
        const res = await request("/detail/" + id);
        return res.data || {};
    },
    async deleteRecord(id) {
        return await request("/delete/" + id, "DELETE");
    },
    async clearAllRecords() {
        return await request("/clear", "DELETE");
    },
    async compareRecords(ids) {
        const params = new URLSearchParams();
        ids.forEach(id => params.append("ids", id));
        const res = await fetch(`${BASE_URL}/compare?${params}`, { headers: getHeaders() });
        const data = await res.json();
        return data.data || [];
    }
};