// MCP 浏览器同步后台服务 (Firefox 兼容版)
const SYNC_SERVER = 'http://100.120.189.27:9978';
let syncEnabled = true;

// 实时同步所有变化
browser.bookmarks.onCreated.addListener(syncBookmarks);
browser.bookmarks.onChanged.addListener(syncBookmarks);
browser.bookmarks.onRemoved.addListener(syncBookmarks);

browser.history.onVisited.addListener(syncHistory);

browser.tabs.onCreated.addListener(syncTabs);
browser.tabs.onUpdated.addListener(syncTabs);
browser.tabs.onRemoved.addListener(syncTabs);

// 定时全量同步（每分钟）
setInterval(() => {
  if (syncEnabled) {
    fullSync();
  }
}, 60000);

// 启动时立即同步
fullSync();

// 同步书签
async function syncBookmarks() {
  try {
    const bookmarks = await browser.bookmarks.getTree();
    const flatBookmarks = flattenBookmarks(bookmarks);

    await fetch(`${SYNC_SERVER}/sync/bookmarks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(flatBookmarks)
    });

    console.log('✅ 书签已同步', flatBookmarks.length);
  } catch (error) {
    console.error('❌ 书签同步失败:', error);
  }
}

// 同步历史
async function syncHistory() {
  try {
    const history = await browser.history.search({ text: '', maxResults: 1000 });

    await fetch(`${SYNC_SERVER}/sync/history`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(history.map(h => ({
        url: h.url,
        title: h.title,
        visitCount: h.visitCount,
        lastVisit: new Date(h.lastVisitTime).toISOString()
      })))
    });

    console.log('✅ 历史已同步', history.length);
  } catch (error) {
    console.error('❌ 历史同步失败:', error);
  }
}

// 同步标签页
async function syncTabs() {
  try {
    const tabs = await browser.tabs.query({});

    await fetch(`${SYNC_SERVER}/sync/tabs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(tabs.map(t => ({
        url: t.url,
        title: t.title,
        active: t.active,
        pinned: t.pinned
      })))
    });

    console.log('✅ 标签页已同步', tabs.length);
  } catch (error) {
    console.error('❌ 标签页同步失败:', error);
  }
}

// 同步 Cookie
async function syncCookies() {
  try {
    const cookies = await browser.cookies.getAll({});

    await fetch(`${SYNC_SERVER}/sync/cookies`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(cookies)
    });

    console.log('✅ Cookies 已同步', cookies.length);
  } catch (error) {
    console.error('❌ Cookies 同步失败:', error);
  }
}

// 全量同步
async function fullSync() {
  console.log('🔄 开始全量同步...');

  try {
    await syncBookmarks();
    await syncHistory();
    await syncTabs();
    await syncCookies();

    console.log('✅ 全量同步完成');

    // 发送通知
    await browser.notifications.create({
      type: 'basic',
      iconUrl: 'icon.png',
      title: 'MCP 浏览器同步',
      message: '所有数据已同步到其他设备'
    });
  } catch (error) {
    console.error('❌ 同步失败:', error);
  }
}

// 从其他设备拉取数据
async function pullFromServer() {
  try {
    const response = await fetch(`${SYNC_SERVER}/sync/all`);
    const data = await response.json();

    // 导入书签
    if (data.bookmarks) {
      for (const bookmark of data.bookmarks) {
        try {
          await browser.bookmarks.create({
            url: bookmark.url,
            title: bookmark.title
          });
        } catch (e) {
          // 书签可能已存在，忽略错误
        }
      }
    }

    // 导入历史
    if (data.history) {
      for (const h of data.history) {
        await browser.history.addUrl({ url: h.url });
      }
    }

    // 导入 Cookies
    if (data.cookies) {
      for (const cookie of data.cookies) {
        await browser.cookies.set({
          url: `http${cookie.secure ? 's' : ''}://${cookie.domain}`,
          name: cookie.name,
          value: cookie.value,
          domain: cookie.domain,
          path: cookie.path
        });
      }
    }

    console.log('✅ 从服务器拉取数据完成');
  } catch (error) {
    console.error('❌ 拉取失败:', error);
  }
}

// 扁平化书签树
function flattenBookmarks(tree, result = []) {
  for (const node of tree) {
    if (node.url) {
      result.push({
        url: node.url,
        title: node.title,
        folder: node.parentId
      });
    }
    if (node.children) {
      flattenBookmarks(node.children, result);
    }
  }
  return result;
}

// 监听来自 popup 的消息
browser.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'fullSync') {
    fullSync();
  } else if (request.action === 'pullSync') {
    pullFromServer();
  } else if (request.action === 'toggleSync') {
    syncEnabled = !syncEnabled;
    sendResponse({ enabled: syncEnabled });
  }
});
