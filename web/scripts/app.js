/**
 * Qingxin Translator - Frontend Application
 */

// 全局状态
const state = {
    currentPage: 'translate',
    isTranslating: false,
    apiReady: false,
    isRecordingHotkey: false,
    streamingText: ''  // 流式翻译累积文本
};

// 等待pywebview API就绪
function waitForApi() {
    return new Promise((resolve) => {
        if (window.pywebview && window.pywebview.api) {
            resolve();
            return;
        }
        
        const checkInterval = setInterval(() => {
            if (window.pywebview && window.pywebview.api) {
                clearInterval(checkInterval);
                resolve();
            }
        }, 100);
        
        setTimeout(() => {
            clearInterval(checkInterval);
            reject(new Error('pywebview API timeout'));
        }, 5000);
    });
}

// DOM元素
const elements = {};

// 初始化DOM元素引用
function initElements() {
    elements.navBtns = document.querySelectorAll('.nav-btn');
    elements.sourceText = document.getElementById('source-text');
    elements.translatedText = document.getElementById('translated-text');
    elements.outputArea = document.getElementById('output-area');
    elements.searchInput = document.getElementById('search-input');
    elements.clearBtn = document.getElementById('clear-btn');
    elements.historyList = document.getElementById('history-list');
    elements.autoCopy = document.getElementById('auto-copy');
    elements.minimizeToTray = document.getElementById('minimize-to-tray');
    elements.launchAtStartup = document.getElementById('launch-at-startup');
    elements.hotkey = document.getElementById('hotkey');
    elements.selectionHotkey = document.getElementById('selection-hotkey');
    elements.apiUrl = document.getElementById('api-url');
    elements.apiKey = document.getElementById('api-key');
    elements.modelSelect = document.getElementById('model-select');
    elements.refreshModelsBtn = document.getElementById('refresh-models');
    elements.testConnectionBtn = document.getElementById('test-connection');
    elements.toggleKeyVisibility = document.getElementById('toggle-key-visibility');
    elements.minimizeBtn = document.getElementById('minimize-btn');
    elements.closeBtn = document.getElementById('close-btn');
    elements.pinBtn = document.getElementById('pin-btn');
    elements.loadingOverlay = document.getElementById('loading-overlay');
    elements.toast = document.getElementById('toast');
}

// API调用封装
async function callApi(method, ...args) {
    try {
        if (window.pywebview && window.pywebview.api) {
            const apiMethod = window.pywebview.api[method];
            if (typeof apiMethod === 'function') {
                return await apiMethod(...args);
            }
        }
        throw new Error('pywebview API not available');
    } catch (error) {
        console.error('API Error:', error);
        showToast('操作失败: ' + error.message, 'error');
        return { success: false, error: error.message };
    }
}

// 显示Toast提示
function showToast(message, type = 'info', duration = 3000) {
    if (!elements.toast) return;
    elements.toast.textContent = message;
    elements.toast.className = 'toast show ' + type;
    
    setTimeout(() => {
        elements.toast.className = 'toast';
    }, duration);
}

// 自定义确认弹窗（替代原生 confirm）
function showConfirm(message, title = '确认操作') {
    return new Promise((resolve) => {
        const overlay = document.getElementById('confirm-modal');
        const titleEl = document.getElementById('confirm-title');
        const messageEl = document.getElementById('confirm-message');
        const cancelBtn = document.getElementById('confirm-cancel');
        const okBtn = document.getElementById('confirm-ok');
        
        titleEl.textContent = title;
        messageEl.textContent = message;
        overlay.classList.add('show');
        
        // 聚焦确定按钮
        setTimeout(() => okBtn.focus(), 100);
        
        function cleanup() {
            overlay.classList.remove('show');
            cancelBtn.removeEventListener('click', onCancel);
            okBtn.removeEventListener('click', onOk);
            overlay.removeEventListener('click', onOverlay);
            document.removeEventListener('keydown', onKeydown);
        }
        
        function onCancel() {
            cleanup();
            resolve(false);
        }
        
        function onOk() {
            cleanup();
            resolve(true);
        }
        
        function onOverlay(e) {
            // 点击遮罩层关闭
            if (e.target === overlay) {
                cleanup();
                resolve(false);
            }
        }
        
        function onKeydown(e) {
            if (e.key === 'Escape') {
                cleanup();
                resolve(false);
            } else if (e.key === 'Enter') {
                cleanup();
                resolve(true);
            }
        }
        
        cancelBtn.addEventListener('click', onCancel);
        okBtn.addEventListener('click', onOk);
        overlay.addEventListener('click', onOverlay);
        document.addEventListener('keydown', onKeydown);
    });
}

// 页面切换
function switchPage(pageName) {
    state.currentPage = pageName;
    
    // 更新导航按钮状态
    elements.navBtns.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.page === pageName);
    });
    
    // 更新页面显示
    document.querySelectorAll('.page').forEach(page => {
        page.classList.toggle('active', page.id === pageName + '-page');
    });
    
    // 调整窗口大小
    if (pageName === 'translate') {
        // 返回翻译页面时，根据当前内容动态计算高度
        setTimeout(() => _autoResizeForContent(), 50);
    } else {
        adjustWindowSize(pageName);
    }
    
    // 加载历史记录
    if (pageName === 'history') {
        loadHistory();
    }
    
    // 加载设置
    if (pageName === 'settings') {
        loadSettings();
    }
}

// 调整窗口大小（每个页面独立的固定高度）
function adjustWindowSize(pageName) {
    if (!window.pywebview || !window.pywebview.api) return;
    
    try {
        const sizes = {
            'translate': { width: 520, height: 210 },   // 48 + 16 + 120 + 16 + 10(余量) = 210
            'history': { width: 520, height: 450 },
            'settings': { width: 520, height: 420 }
        };
        const size = sizes[pageName] || sizes['translate'];
        window.pywebview.api.resize(size.width, size.height);
    } catch (e) {}
}

// 根据内容自动调整翻译页面窗口高度
// 计算公式：标题栏 + 上间距 + 输入框 + 间距(有译文时) + 译文框 + 下间距
function _autoResizeForContent() {
    if (!window.pywebview || !window.pywebview.api) return;
    if (state.currentPage !== 'translate') return;
    
    try {
        const TITLE_BAR = 48;
        const PADDING_TOP = 16;
        const PADDING_BOTTOM = 16;
        const GAP = 12; // output-area 的 margin-top
        
        const inputHeight = elements.sourceText ? elements.sourceText.offsetHeight : 120;
        
        const outputVisible = elements.outputArea 
            && elements.outputArea.classList.contains('visible');
        
        let outputHeight = 0;
        if (outputVisible) {
            const textContent = elements.translatedText ? elements.translatedText.textContent : '';
            if (textContent && textContent.trim()) {
                // 译文框高度 = 文本高度 + 操作栏(~48px) + output-area padding(12*2) + 边框(2)
                const textHeight = elements.translatedText.scrollHeight;
                const actionsHeight = 48; // 按钮32 + margin-top8 + padding-top8
                outputHeight = textHeight + actionsHeight + 12 + 12 + 2;
            }
        }
        
        // 精确计算
        const totalHeight = TITLE_BAR + PADDING_TOP + inputHeight 
            + (outputHeight > 0 ? GAP + outputHeight : 0) 
            + PADDING_BOTTOM;
        
        window.pywebview.api.resize(520, totalHeight);
    } catch (e) {}
}

// 流式翻译回调（由 Python 端 evaluate_js 调用）
window.__onTranslateChunk = function(chunk) {
    state.streamingText += chunk;
    if (elements.translatedText) {
        elements.translatedText.textContent = state.streamingText;
        elements.translatedText.className = '';
    }
    // 流式过程中动态调整窗口高度
    _autoResizeForContent();
};

window.__onTranslateDone = function() {
    state.isTranslating = false;
    if (elements.translatedText) {
        elements.translatedText.className = '';
    }
    // 翻译完成后再调整一次
    _autoResizeForContent();
};

window.__onTranslateError = function(error) {
    state.isTranslating = false;
    if (elements.translatedText) {
        elements.translatedText.textContent = error || '翻译失败';
        elements.translatedText.className = 'error';
    }
};

// 翻译文本（流式显示）
async function translate(text) {
    if (!text || !text.trim() || state.isTranslating) {
        if (!text || !text.trim()) {
            _collapseOutputArea();
        }
        return;
    }
    
    state.isTranslating = true;
    state.streamingText = '';
    
    // 翻译期间：显示译文区域
    elements.outputArea.classList.add('visible');
    elements.translatedText.textContent = '';
    elements.translatedText.className = 'translating';
    
    try {
        const result = await callApi('translate', text);
        
        if (result.success) {
            elements.translatedText.textContent = result.translation;
            elements.translatedText.className = '';
        } else {
            elements.translatedText.textContent = result.error || '翻译失败';
            elements.translatedText.className = 'error';
        }
        
        // 翻译完成后才展开窗口
        _expandOutputArea();
        
    } catch (error) {
        elements.translatedText.textContent = '翻译请求失败';
        elements.translatedText.className = 'error';
        _expandOutputArea();
    } finally {
        state.isTranslating = false;
    }
}

// 展开译文区域并调整窗口高度
function _expandOutputArea() {
    elements.outputArea.classList.add('visible');
    // 等动画开始后再调整窗口高度（匹配 CSS 过渡时间）
    setTimeout(() => _autoResizeForContent(), 50);
    setTimeout(() => _autoResizeForContent(), 350);
}

// 收起译文区域（带过渡动画）
function _collapseOutputArea() {
    if (!elements.outputArea || !elements.outputArea.classList.contains('visible')) return;
    
    elements.outputArea.classList.remove('visible');
    
    // 同步调整窗口高度
    setTimeout(() => _autoResizeForContent(), 50);
    
    // 动画结束后清空内容
    setTimeout(() => {
        elements.translatedText.textContent = '';
        _autoResizeForContent();
    }, 400);
}

// 复制译文
async function copyTranslation() {
    const text = elements.translatedText.textContent;
    if (!text || text === '翻译中...' || text.includes('失败')) {
        return;
    }
    
    try {
        await navigator.clipboard.writeText(text);
        showToast('已复制到剪贴板', 'success');
    } catch (error) {
        showToast('复制失败', 'error');
    }
}

// 朗读译文
async function speakTranslation() {
    const text = elements.translatedText.textContent;
    if (!text || text === '翻译中...' || text.includes('失败')) {
        return;
    }
    
    try {
        if ('speechSynthesis' in window) {
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'en-US';
            window.speechSynthesis.speak(utterance);
            showToast('正在朗读...', 'info', 2000);
        } else {
            showToast('您的浏览器不支持语音合成', 'error');
        }
    } catch (error) {
        showToast('朗读失败', 'error');
    }
}

// 加载历史记录
async function loadHistory(keyword = null) {
    try {
        const records = await callApi('get_history', keyword);
        renderHistoryList(records);
    } catch (error) {
        console.error('加载历史记录失败:', error);
    }
}

// 渲染历史记录列表
function renderHistoryList(records) {
    if (!records || records.length === 0) {
        elements.historyList.innerHTML = `
            <div class="empty-state">
                <svg class="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
                <div class="empty-state-text">暂无历史记录</div>
            </div>
        `;
        return;
    }
    
    elements.historyList.innerHTML = records.map(record => `
        <div class="history-item" data-id="${record.id}">
            <div class="history-item-header">
                <span class="history-time">${formatTime(record.created_at)}</span>
            </div>
            <div class="history-original">${escapeHtml(record.source_text)}</div>
            <div class="history-translated">${escapeHtml(record.translated_text)}</div>
            <div class="history-actions">
                <button class="history-action-btn copy-btn" onclick="copyHistoryText('${escapeHtml(record.translated_text)}')" title="复制">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                        <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
                    </svg>
                </button>
                <button class="history-action-btn delete-btn" onclick="deleteHistory(${record.id})" title="删除">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                        <line x1="10" y1="11" x2="10" y2="17"/>
                        <line x1="14" y1="11" x2="14" y2="17"/>
                    </svg>
                </button>
            </div>
        </div>
    `).join('');
}

// 格式化时间
function formatTime(isoString) {
    try {
        const date = new Date(isoString);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return isoString;
    }
}

// HTML转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 复制历史记录文本
async function copyHistoryText(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('已复制到剪贴板', 'success');
    } catch (error) {
        showToast('复制失败', 'error');
    }
}

// 删除历史记录
async function deleteHistory(id) {
    try {
        const result = await callApi('delete_history', id);
        if (result.success) {
            showToast('已删除', 'success');
            loadHistory();
        } else {
            showToast(result.error || '删除失败', 'error');
        }
    } catch (error) {
        showToast('删除失败', 'error');
    }
}

// 清空历史记录
async function clearHistory() {
    const confirmed = await showConfirm('确定要清空所有历史记录吗？此操作不可撤销。', '清空历史');
    if (!confirmed) {
        return;
    }
    
    try {
        const result = await callApi('clear_history');
        if (result.success) {
            showToast('已清空历史记录', 'success');
            loadHistory();
        } else {
            showToast(result.error || '清空失败', 'error');
        }
    } catch (error) {
        showToast('清空失败', 'error');
    }
}

// 加载设置（不显示提示）
async function loadSettings() {
    try {
        const settings = await callApi('get_settings');
        
        // 通用设置
        elements.autoCopy.checked = settings.auto_copy !== false;
        elements.minimizeToTray.checked = settings.minimize_to_tray !== false;
        elements.launchAtStartup.checked = settings.launch_at_startup === true;
        elements.hotkey.value = settings.hotkey || '';
        elements.selectionHotkey.value = settings.selection_translate_hotkey || '';
        
        // 翻译引擎设置
        elements.apiUrl.value = settings.api_url || '';
        elements.apiKey.value = settings.api_key || '';
        
        // 加载模型列表并恢复上次选择
        if (settings.api_url && settings.api_key) {
            await refreshModels(settings.api_model);
        }
    } catch (error) {
        console.error('加载设置失败:', error);
    }
}

// 保存设置
async function saveSettings(showNotification = false) {
    const settings = {
        auto_copy: elements.autoCopy.checked,
        minimize_to_tray: elements.minimizeToTray.checked,
        hotkey: elements.hotkey.value,
        selection_translate_hotkey: elements.selectionHotkey.value,
        api_url: elements.apiUrl.value,
        api_key: elements.apiKey.value,
        api_model: elements.modelSelect.value
    };
    
    try {
        const result = await callApi('save_settings', settings);
        if (result.success && showNotification) {
            showToast('设置已保存', 'success');
        }
    } catch (error) {
        if (showNotification) {
            showToast('保存失败', 'error');
        }
    }
}

// 刷新模型列表
async function refreshModels(selectModel = null) {
    const apiUrl = elements.apiUrl.value;
    const apiKey = elements.apiKey.value;
    
    if (!apiUrl || !apiKey) {
        return;
    }
    
    try {
        const result = await callApi('get_models', apiUrl, apiKey);
        
        if (result.success && result.models) {
            // 清空并填充模型列表
            elements.modelSelect.innerHTML = '<option value="">请选择模型</option>';
            result.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = model.id;
                elements.modelSelect.appendChild(option);
            });
            
            // 选择指定模型或第一个模型
            if (selectModel && result.models.some(m => m.id === selectModel)) {
                elements.modelSelect.value = selectModel;
            } else if (result.models.length > 0) {
                elements.modelSelect.value = result.models[0].id;
            }
        }
    } catch (error) {
        console.error('获取模型列表失败:', error);
    }
}

// 测试连接
async function testConnection() {
    const apiUrl = elements.apiUrl.value;
    const apiKey = elements.apiKey.value;
    const model = elements.modelSelect.value;
    
    if (!apiUrl || !apiKey || !model) {
        showToast('请填写完整的API配置', 'error');
        return;
    }
    
    try {
        const result = await callApi('test_connection', apiUrl, apiKey, model);
        
        if (result.success) {
            showToast(result.message || '连接测试成功', 'success');
        } else {
            showToast(result.error || '连接测试失败', 'error');
        }
    } catch (error) {
        showToast('连接测试失败', 'error');
    }
}

// 切换API Key显示/隐藏
function toggleApiKeyVisibility() {
    const type = elements.apiKey.type === 'password' ? 'text' : 'password';
    elements.apiKey.type = type;
}

// 快捷键录制
let activeRecordingInput = null; // 当前正在录制的输入框

function startHotkeyRecording(targetElement) {
    state.isRecordingHotkey = true;
    activeRecordingInput = targetElement;
    targetElement.value = '请按下快捷键...';
    targetElement.classList.add('recording');
}

function stopHotkeyRecording() {
    state.isRecordingHotkey = false;
    if (activeRecordingInput) {
        activeRecordingInput.classList.remove('recording');
        activeRecordingInput = null;
    }
}

// 键盘事件处理
function handleKeydown(e) {
    if (!state.isRecordingHotkey || !activeRecordingInput) return;
    
    e.preventDefault();
    e.stopPropagation();
    
    // 构建快捷键字符串
    const keys = [];
    if (e.ctrlKey) keys.push('Ctrl');
    if (e.shiftKey) keys.push('Shift');
    if (e.altKey) keys.push('Alt');
    if (e.metaKey) keys.push('Cmd');
    
    // 添加主键（排除修饰键）
    const key = e.key;
    const modifierKeys = ['Control', 'Shift', 'Alt', 'Meta'];
    
    if (!modifierKeys.includes(key)) {
        // 将功能键转换为可读格式
        let keyName = key;
        if (key === ' ') keyName = 'Space';
        else if (key === 'ArrowUp') keyName = 'Up';
        else if (key === 'ArrowDown') keyName = 'Down';
        else if (key === 'ArrowLeft') keyName = 'Left';
        else if (key === 'ArrowRight') keyName = 'Right';
        else if (key.length === 1) keyName = key.toUpperCase();
        
        keys.push(keyName);
        
        // 只有在按下主键时才保存（至少一个修饰键 + 一个主键）
        if (keys.length >= 2) {
            activeRecordingInput.value = keys.join('+');
            stopHotkeyRecording();
            saveSettings(false);
        }
    }
}

// 最小化窗口
function minimizeWindow() {
    callApi('minimize_window');
}

// 关闭窗口
function closeWindow() {
    callApi('close_window');
}

// 切换钉住（置顶）
function togglePin() {
    const btn = elements.pinBtn;
    const isPinned = btn.classList.toggle('pinned');
    btn.title = isPinned ? '取消钉住' : '钉住窗口';
    callApi('set_on_top', isPinned);
}

// 事件绑定
function bindEvents() {
    // 导航按钮
    elements.navBtns.forEach(btn => {
        btn.addEventListener('click', () => switchPage(btn.dataset.page));
    });
    
    // 翻译输入（处理中文输入法 + 300ms 防抖）
    let translateTimer;
    let isComposing = false;  // 是否正在使用输入法
    
    // 监听输入法组合事件
    elements.sourceText.addEventListener('compositionstart', () => {
        isComposing = true;
    });
    
    elements.sourceText.addEventListener('compositionend', (e) => {
        isComposing = false;
        // 输入法提交后，触发翻译
        clearTimeout(translateTimer);
        translateTimer = setTimeout(() => {
            translate(e.target.value);
        }, 100);
    });
    
    elements.sourceText.addEventListener('input', (e) => {
        // 如果正在使用输入法，不触发翻译
        if (isComposing) return;
        
        clearTimeout(translateTimer);
        translateTimer = setTimeout(() => {
            translate(e.target.value);
        }, 300);
    });
    
    // 历史记录搜索
    let searchTimer;
    elements.searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => {
            loadHistory(e.target.value);
        }, 300);
    });
    
    // 清空历史
    elements.clearBtn.addEventListener('click', clearHistory);
    
    // 设置输入变化自动保存（不显示提示）
    // checkbox/select 用 change 事件
    [elements.autoCopy, elements.minimizeToTray, elements.modelSelect].forEach(input => {
        input.addEventListener('change', () => saveSettings(false));
    });
    
    // 开机自启动（单独处理，需要操作注册表）
    elements.launchAtStartup.addEventListener('change', async (e) => {
        const enable = e.target.checked;
        const result = await callApi('set_startup', enable);
        if (!result.success) {
            // 失败时恢复开关状态
            e.target.checked = !enable;
            showToast(result.error || '设置开机自启失败', 'error');
        }
    });
    // 文本输入同时监听 input 事件（change 只在失焦时触发，容易丢失）
    let saveTimer;
    [elements.apiUrl, elements.apiKey].forEach(input => {
        input.addEventListener('input', () => {
            clearTimeout(saveTimer);
            saveTimer = setTimeout(() => saveSettings(false), 500);
        });
        input.addEventListener('change', () => saveSettings(false));
    });
    
    // 快捷键输入框
    elements.hotkey.addEventListener('click', () => startHotkeyRecording(elements.hotkey));
    elements.selectionHotkey.addEventListener('click', () => startHotkeyRecording(elements.selectionHotkey));
    document.addEventListener('keydown', handleKeydown);
    
    // 模型相关按钮
    elements.refreshModelsBtn.addEventListener('click', () => refreshModels());
    elements.testConnectionBtn.addEventListener('click', testConnection);
    
    // API Key可见性切换
    elements.toggleKeyVisibility.addEventListener('click', toggleApiKeyVisibility);
    
    // 窗口控制
    elements.minimizeBtn.addEventListener('click', minimizeWindow);
    elements.closeBtn.addEventListener('click', closeWindow);
    elements.pinBtn.addEventListener('click', togglePin);
    
    // 译文区域按钮
    document.getElementById('copy-translation').addEventListener('click', copyTranslation);
    document.getElementById('speak-translation').addEventListener('click', speakTranslation);
}

// 窗口拖动功能
function initDrag() {
    const titleBar = document.querySelector('.title-bar');
    if (!titleBar) return;
    
    let isDragging = false;
    let lastMouseX = 0;
    let lastMouseY = 0;
    
    titleBar.addEventListener('mousedown', (e) => {
        // 如果点击的是按钮区域，不触发拖动
        if (e.target.closest('.nav-icons') || e.target.closest('.window-controls')) {
            return;
        }
        
        // 防止文本选择
        e.preventDefault();
        
        // 记录鼠标起始位置
        lastMouseX = e.screenX;
        lastMouseY = e.screenY;
        isDragging = true;
    });
    
    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        
        // 计算鼠标移动的增量
        const deltaX = e.screenX - lastMouseX;
        const deltaY = e.screenY - lastMouseY;
        
        // 更新鼠标位置
        lastMouseX = e.screenX;
        lastMouseY = e.screenY;
        
        // 使用相对移动（基于当前位置偏移）
        callApi('move_relative', deltaX, deltaY);
    });
    
    document.addEventListener('mouseup', () => {
        isDragging = false;
    });
}

// 划词翻译结果回调（由后端 evaluate_js 调用）
window.__onSelectionTranslate = function(sourceText, translation) {
    console.log('Selection translate result:', sourceText, '->', translation);
    
    // 切换到翻译页面
    switchPage('translate');
    
    // 设置原文
    elements.sourceText.value = sourceText;
    
    // 显示译文区域并设置译文
    elements.outputArea.classList.add('visible');
    elements.translatedText.textContent = translation;
    elements.translatedText.className = '';
    
    // 根据内容自动调整窗口高度
    setTimeout(() => _autoResizeForContent(), 50);
    setTimeout(() => _autoResizeForContent(), 350);
    
    // 让窗口获得焦点（触发 onfocus 事件）
    window.focus();
    
    showToast('划词翻译完成', 'success', 2000);
};

// 初始化
async function init() {
    initElements();
    
    try {
        await waitForApi();
        state.apiReady = true;
        bindEvents();
        initDrag();
        loadSettings();
        
        // 延迟调整窗口大小，确保 DOM 已完全渲染
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                adjustWindowSize('translate');
            });
        });
    } catch (error) {
        console.error('API初始化失败:', error);
        showToast('应用初始化失败，请重启', 'error');
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init);
