// Popup 控制脚本 (Firefox 兼容)
document.getElementById('pushBtn').addEventListener('click', () => {
  browser.runtime.sendMessage({ action: 'fullSync' });
  showMessage('正在推送数据到其他设备...');
});

document.getElementById('pullBtn').addEventListener('click', () => {
  browser.runtime.sendMessage({ action: 'pullSync' });
  showMessage('正在从其他设备拉取数据...');
});

document.getElementById('toggleBtn').addEventListener('click', () => {
  browser.runtime.sendMessage({ action: 'toggleSync' }, (response) => {
    showMessage(response.enabled ? '自动同步已启用' : '自动同步已暂停');
  });
});

function showMessage(msg) {
  const status = document.querySelector('.status');
  status.innerHTML = `<div style="color: #2196F3; font-weight: bold;">${msg}</div>`;

  setTimeout(() => {
    status.innerHTML = `
      <div>服务器: <span class="connected">100.120.189.27:9978</span></div>
      <div>同步内容: 书签、历史、标签、Cookies</div>
      <div>同步频率: 每分钟 + 实时</div>
    `;
  }, 2000);
}
