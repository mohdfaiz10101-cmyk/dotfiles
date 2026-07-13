// ==UserScript==
// @name         Claude 自动登录
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  自动填充 Claude 账号密码并登录
// @author       Charlie
// @match        https://claude.ai/*
// @match        https://*.anthropic.com/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function() {
    'use strict';

    const ACCOUNT = {
        email: "MahaSarmila523@gmail.com",
        password: "kb9qr6fuop"
    };

    function log(msg) {
        console.log(`[Claude Auto Login] ${msg}`);
    }

    function autoFill() {
        // 等待页面完全加载
        setTimeout(() => {
            const emailInput = document.querySelector('input[type="email"]') ||
                             document.querySelector('input[name="email"]') ||
                             document.querySelector('[placeholder*="email" i]');

            const passwordInput = document.querySelector('input[type="password"]') ||
                                document.querySelector('input[name="password"]');

            const submitBtn = document.querySelector('button[type="submit"]') ||
                            document.querySelector('button:contains("Sign in")') ||
                            document.querySelector('button:contains("Continue")');

            if (emailInput && !emailInput.value) {
                emailInput.value = ACCOUNT.email;
                emailInput.dispatchEvent(new Event('input', { bubbles: true }));
                emailInput.dispatchEvent(new Event('change', { bubbles: true }));
                log('✅ 邮箱已填充');
            }

            if (passwordInput && !passwordInput.value) {
                passwordInput.value = ACCOUNT.password;
                passwordInput.dispatchEvent(new Event('input', { bubbles: true }));
                passwordInput.dispatchEvent(new Event('change', { bubbles: true }));
                log('✅ 密码已填充');
            }

            // 自动点击提交按钮
            if (submitBtn && emailInput && passwordInput && emailInput.value && passwordInput.value) {
                setTimeout(() => {
                    submitBtn.click();
                    log('✅ 自动提交登录');
                }, 800);
            }
        }, 1500);
    }

    // 页面加载完成后自动填充
    if (document.readyState === 'complete') {
        autoFill();
    } else {
        window.addEventListener('load', autoFill);
    }

    // 监听 URL 变化（SPA 页面）
    let lastUrl = location.href;
    new MutationObserver(() => {
        const url = location.href;
        if (url !== lastUrl) {
            lastUrl = url;
            autoFill();
        }
    }).observe(document, {subtree: true, childList: true});

})();
