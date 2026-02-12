/**
 * SGA Aurora — Notification System (Alpine.js Unified)
 * 
 * This module handles:
 * - WebSocket real-time notifications
 * - Badge count updates
 * - Dropdown content updates (delegated to Alpine.js for visibility)
 * - Individual notification mark-as-read via API
 */
document.addEventListener('DOMContentLoaded', function () {
    if (!window.SGA_CONFIG) {
        console.warn('[SGA] SGA_CONFIG não encontrado. Notificações desativadas.');
        return;
    }

    const config = window.SGA_CONFIG;

    // =====================================================
    // MARK-AS-READ (click handler on dropdown items)
    // =====================================================
    const dropdown = document.getElementById('notificationsDropdown');

    if (dropdown) {
        dropdown.addEventListener('click', function (e) {
            const item = e.target.closest('.notification-item');
            if (!item) return;

            const notificationId = item.getAttribute('data-id');
            const actionLink = e.target.closest('.notification-action');

            // Mark as read if unread
            const indicator = item.querySelector('.unread-indicator');
            if (indicator) {
                marcarComoLida(notificationId, item);
            }

            // If clicked on the item body (not the link), navigate to the link
            if (!actionLink) {
                const targetLink = item.querySelector('.notification-action');
                if (targetLink && targetLink.href && targetLink.href !== '#') {
                    e.preventDefault();
                    window.location.href = targetLink.href;
                }
            }
        });
    }

    function marcarComoLida(id, element) {
        if (!id) return;
        fetch(config.markReadUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': config.csrfToken,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ notification_id: id })
        })
            .then(r => r.json())
            .then(data => {
                if (data.status === 'ok') {
                    // Remove unread indicator
                    if (element) {
                        const dot = element.querySelector('.unread-indicator');
                        if (dot) dot.remove();
                    }
                    // Decrement badge
                    atualizarBadgeNotificacoes(Math.max(0, getBadgeCount() - 1));

                    // Inform WebSocket 
                    if (window.notificationSocket && window.notificationSocket.readyState === WebSocket.OPEN) {
                        window.notificationSocket.send(JSON.stringify({ action: 'mark_read', notification_id: id }));
                    }
                }
            })
            .catch(err => console.error('[SGA] Erro ao marcar notificação:', err));
    }

    // =====================================================
    // BADGE COUNT HELPERS
    // =====================================================
    function getBadgeCount() {
        const badge = document.getElementById('notificationCount');
        if (!badge) return 0;
        return parseInt(badge.textContent) || 0;
    }

    function atualizarBadgeNotificacoes(count) {
        const badge = document.getElementById('notificationCount');
        const bellBtn = document.getElementById('notificationBell');

        if (count > 0) {
            if (badge) {
                badge.textContent = count;
                badge.closest('.notification-badge-wrap').style.display = '';
            } else if (bellBtn) {
                // Create badge dynamically if it doesn't exist
                const wrap = document.createElement('span');
                wrap.className = 'notification-badge-wrap absolute top-1.5 right-1.5 flex h-4 w-4';
                wrap.innerHTML = `
                    <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-sga-red opacity-75"></span>
                    <span id="notificationCount" class="relative inline-flex rounded-full h-4 w-4 bg-sga-red items-center justify-center text-[10px] text-white font-bold">${count}</span>
                `;
                bellBtn.style.position = 'relative';
                bellBtn.appendChild(wrap);
            }
        } else {
            if (badge) {
                const wrap = badge.closest('.notification-badge-wrap');
                if (wrap) wrap.style.display = 'none';
            }
        }
    }

    // =====================================================
    // WEBSOCKET REAL-TIME CONNECTION
    // =====================================================
    if (config.isAuthenticated) {
        window.notificationSocket = null;
        let reconnectAttempts = 0;
        const maxReconnectAttempts = 5;

        function connectWebSocket() {
            console.log('[WS] A conectar...');
            window.notificationSocket = new WebSocket(config.wsUrl);

            window.notificationSocket.onopen = function () {
                console.log('[WS] ✅ Conectado');
                reconnectAttempts = 0;
            };

            window.notificationSocket.onmessage = function (e) {
                const data = JSON.parse(e.data);
                console.log('[WS] Mensagem:', data);

                // Update badge count
                if (data.type === 'notification_count' || data.type === 'new_notification') {
                    atualizarBadgeNotificacoes(data.count);
                }

                // Show toast for new notification
                if (data.type === 'new_notification') {
                    mostrarToastNotificacao(data.message, data.link);
                    buscarNotificacoesViaAPI();
                }

                // Dispatch event for pending confirmations page
                if (data.type === 'pendencia_update' || data.type === 'new_notification') {
                    window.dispatchEvent(new CustomEvent('pendenciasAtualizadas', { detail: data }));
                }
            };

            window.notificationSocket.onclose = function (e) {
                console.log('[WS] ⚠️ Desconectado:', e.code);
                if (reconnectAttempts < maxReconnectAttempts) {
                    reconnectAttempts++;
                    const delay = 3000 * reconnectAttempts;
                    console.log(`[WS] Reconectando em ${delay / 1000}s...`);
                    setTimeout(connectWebSocket, delay);
                }
            };

            window.notificationSocket.onerror = function (e) {
                console.error('[WS] ❌ Erro:', e);
            };
        }

        // Show a toast when a new notification arrives
        function mostrarToastNotificacao(message, link) {
            if (typeof Toastify === 'function') {
                Toastify({
                    text: `🔔 ${message}`,
                    duration: 6000,
                    gravity: 'top',
                    position: 'right',
                    className: 'modern-toast',
                    stopOnFocus: true,
                    onClick: function () {
                        if (link && link !== '#') window.location.href = link;
                    },
                    style: {
                        background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
                        borderRadius: '16px',
                        boxShadow: '0 20px 25px -5px rgba(0,0,0,0.15)',
                        fontFamily: 'Inter, sans-serif',
                        fontWeight: '600',
                        padding: '14px 20px',
                        fontSize: '13px'
                    }
                }).showToast();
            }
        }

        // Fetch full notification list from API and update dropdown HTML
        function buscarNotificacoesViaAPI() {
            fetch(config.checkNotificationsUrl)
                .then(r => r.json())
                .then(data => {
                    atualizarDropdownCompleto(data.notificacoes || []);
                })
                .catch(err => console.error('[WS] Erro ao buscar notificações:', err));
        }

        function atualizarDropdownCompleto(notificacoes) {
            const dropdownEl = document.getElementById('notificationsDropdown');
            if (!dropdownEl) return;

            const listContainer = dropdownEl.querySelector('.notification-list');
            if (!listContainer) return;

            // Clear existing items
            listContainer.innerHTML = '';

            if (notificacoes.length === 0) {
                listContainer.innerHTML = `
                    <div class="p-8 text-center">
                        <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="text-slate-200 mx-auto mb-2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                        <p class="text-sm text-slate-400 font-medium">Nenhuma notificação</p>
                    </div>
                `;
                return;
            }

            notificacoes.forEach(n => {
                const item = document.createElement('div');
                item.className = 'notification-item group p-4 border-b border-slate-50 hover:bg-slate-50/80 transition-colors flex gap-3 cursor-pointer';
                item.setAttribute('data-id', n.id);
                item.innerHTML = `
                    <div class="flex-1 min-w-0">
                        <p class="text-sm text-slate-700 font-medium leading-tight group-hover:text-slate-900 truncate">${n.mensagem}</p>
                        <div class="mt-2 flex items-center justify-between">
                            <span class="text-[11px] text-slate-400 font-medium italic">${n.data || 'Agora'}</span>
                            <a href="${n.link || '#'}" class="notification-action text-[11px] font-bold text-sga-red hover:underline flex items-center gap-1">
                                Abrir <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m9 18 6-6-6-6"/></svg>
                            </a>
                        </div>
                    </div>
                    ${!n.lida ? '<span class="unread-indicator w-2 h-2 bg-blue-500 rounded-full mt-1.5 flex-shrink-0 shadow-sm shadow-blue-200"></span>' : ''}
                `;
                listContainer.appendChild(item);
            });
        }

        // Start WebSocket connection
        connectWebSocket();
    }
});
