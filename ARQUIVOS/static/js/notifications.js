document.addEventListener('DOMContentLoaded', function () {
    // Verificar se a configuração existe
    if (!window.SGA_CONFIG) {
        console.warn('SGA_CONFIG não encontrado. Notificações desativadas.');
        return;
    }

    const config = window.SGA_CONFIG;

    // ==========================================================
    // LÓGICA DO DROPDOWN DE NOTIFICAÇÕES
    // ==========================================================
    const bell = document.getElementById('notificationBell');
    const dropdown = document.getElementById('notificationsDropdown');
    const countBadge = document.getElementById('notificationCount');

    if (bell && dropdown) {
        bell.addEventListener('click', function (e) {
            e.stopPropagation();
            dropdown.classList.toggle('show');
            // Nota: Não marcamos mais tudo como lido ao abrir o sino, 
            // seguindo a nova lógica de marcação individual ou botão "Marcar Tudo".
        });

        // Clique individual na notificação
        dropdown.addEventListener('click', function (e) {
            const item = e.target.closest('.notification-item');
            if (!item) return;

            const notificationId = item.getAttribute('data-id');
            const actionLink = e.target.closest('.notification-action');

            // Se for não lida, marcar como lida
            if (item.classList.contains('unread')) {
                marcarComoLida(notificationId, item);
            }

            // Se clicou explicitamente no link de ação, deixa o navegador seguir
            // Se clicou em qualquer outra parte do item, podemos redirecionar para o link também
            if (!actionLink && item.querySelector('.notification-action')) {
                e.preventDefault();
                const targetUrl = item.querySelector('.notification-action').href;
                if (targetUrl && targetUrl !== '#') {
                    window.location.href = targetUrl;
                }
            }
        });

        document.addEventListener('click', function () {
            if (dropdown.classList.contains('show')) {
                dropdown.classList.remove('show');
            }
        });

        dropdown.addEventListener('click', function (e) {
            e.stopPropagation();
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
            .then(response => response.json())
            .then(data => {
                if (data.status === 'ok') {
                    if (element) {
                        element.classList.remove('unread');
                        const indicator = element.querySelector('.unread-indicator');
                        if (indicator) indicator.remove();
                    }

                    // Decrementar countBadge
                    const countBadge = document.getElementById('notificationCount');
                    if (countBadge) {
                        let currentCount = parseInt(countBadge.innerText) || 0;
                        if (currentCount > 1) {
                            countBadge.innerText = currentCount - 1;
                        } else {
                            countBadge.style.display = 'none';
                        }
                    }

                    // Informar WebSocket
                    if (window.notificationSocket && window.notificationSocket.readyState === WebSocket.OPEN) {
                        window.notificationSocket.send(JSON.stringify({ action: 'mark_read', notification_id: id }));
                    }
                }
            });
    }

    // ==========================================================
    // WEBSOCKET EM TEMPO REAL
    // ==========================================================
    if (config.isAuthenticated) {
        // Variável global para o socket
        window.notificationSocket = null;
        let reconnectAttempts = 0;
        const maxReconnectAttempts = 5;

        function connectWebSocket() {
            console.log('[WS] A conectar ao servidor de notificações...');
            window.notificationSocket = new WebSocket(config.wsUrl);

            window.notificationSocket.onopen = function (e) {
                console.log('[WS] ✅ Conectado ao servidor de notificações');
                reconnectAttempts = 0;
            };

            window.notificationSocket.onmessage = function (e) {
                const data = JSON.parse(e.data);
                console.log('[WS] Mensagem recebida:', data);

                // Atualizar contagem de notificações
                if (data.type === 'notification_count' || data.type === 'new_notification') {
                    atualizarBadgeNotificacoes(data.count);
                }

                // Mostrar nova notificação no dropdown E buscar lista atualizada
                if (data.type === 'new_notification') {
                    adicionarNotificacaoDropdown(data.message, data.link);
                    // Buscar lista completa de notificações
                    buscarNotificacoesViaAPI();
                }

                // Atualizar lista de pendências (se estiver na página)
                if (data.type === 'pendencia_update' || data.type === 'new_notification') {
                    // Disparar evento customizado para a página de pendências
                    window.dispatchEvent(new CustomEvent('pendenciasAtualizadas', {
                        detail: data
                    }));
                    console.log('[WS] Evento pendenciasAtualizadas disparado:', data.type);
                }
            };

            window.notificationSocket.onclose = function (e) {
                console.log('[WS] ⚠️ Conexão fechada. Código:', e.code);
                if (reconnectAttempts < maxReconnectAttempts) {
                    reconnectAttempts++;
                    const delay = 3000 * reconnectAttempts;
                    console.log(`[WS] Tentando reconectar em ${delay / 1000}s... (tentativa ${reconnectAttempts}/${maxReconnectAttempts})`);
                    setTimeout(connectWebSocket, delay);
                } else {
                    console.error('[WS] ❌ Máximo de tentativas de reconexão atingido');
                }
            };

            window.notificationSocket.onerror = function (e) {
                console.error('[WS] ❌ Erro na conexão:', e);
            };
        }

        function atualizarBadgeNotificacoes(count) {
            let badge = document.getElementById('notificationCount');
            const bellElement = document.getElementById('notificationBell');

            if (count > 0) {
                if (!badge && bellElement) {
                    badge = document.createElement('div');
                    badge.id = 'notificationCount';
                    badge.className = 'notification-count';
                    bellElement.appendChild(badge);
                }
                if (badge) {
                    badge.innerText = count;
                    badge.style.display = 'flex';
                }
            } else if (badge) {
                badge.style.display = 'none';
            }
        }

        function adicionarNotificacaoDropdown(mensagem, link) {
            const dropdownEl = document.getElementById('notificationsDropdown');
            if (!dropdownEl) return;

            const novaNotificacao = document.createElement('div');
            novaNotificacao.className = 'notification-item unread';
            // Nota: ID temporário até que o WS envie o ID real ou seja recarregado
            novaNotificacao.innerHTML = `
                <div class="notification-content">
                    <span class="notification-message">${mensagem}</span>
                    <div class="notification-meta">
                        <small class="notification-time">Agora mesmo</small>
                        <a href="${link || '#'}" class="notification-action">Abrir Documento ➔</a>
                    </div>
                </div>
                <div class="unread-indicator"></div>
            `;

            // Inserir após o header do dropdown
            const header = dropdownEl.querySelector('div');
            if (header && header.nextSibling) {
                dropdownEl.insertBefore(novaNotificacao, header.nextSibling);
            } else {
                dropdownEl.appendChild(novaNotificacao);
            }

            // Remover "Nenhuma notificação" se existir
            const emptyMsg = dropdownEl.querySelector('div[style*="text-align: center"]');
            if (emptyMsg && emptyMsg.textContent.includes('Nenhuma notificação')) {
                emptyMsg.remove();
            }
        }

        function buscarNotificacoesViaAPI() {
            // Buscar lista completa de notificações para atualizar o dropdown
            fetch(config.checkNotificationsUrl)
                .then(response => response.json())
                .then(data => {
                    console.log('[WS] Notificações atualizadas via API:', data);
                    atualizarDropdownCompleto(data.notificacoes || []);
                })
                .catch(error => console.error('[WS] Erro ao buscar notificações:', error));
        }

        function atualizarDropdownCompleto(notificacoes) {
            const dropdownEl = document.getElementById('notificationsDropdown');
            if (!dropdownEl) return;

            // Manter apenas o header
            const header = dropdownEl.querySelector('div');
            dropdownEl.innerHTML = '';
            if (header) {
                dropdownEl.appendChild(header.cloneNode(true));
            } else {
                const newHeader = document.createElement('div');
                newHeader.style.cssText = 'padding: 1rem; font-weight: bold; border-bottom: 1px solid #eee;';
                newHeader.textContent = 'Notificações';
                dropdownEl.appendChild(newHeader);
            }

            if (notificacoes.length === 0) {
                const emptyDiv = document.createElement('div');
                emptyDiv.style.cssText = 'padding: 1rem; text-align: center;';
                emptyDiv.textContent = 'Nenhuma notificação.';
                dropdownEl.appendChild(emptyDiv);
            } else {
                notificacoes.forEach(n => {
                    const item = document.createElement('div');
                    item.className = `notification-item ${n.lida ? '' : 'unread'}`;
                    item.setAttribute('data-id', n.id);
                    item.innerHTML = `
                        <div class="notification-content">
                            <span class="notification-message">${n.mensagem}</span>
                            <div class="notification-meta">
                                <small class="notification-time">${n.data || ''}</small>
                                <a href="${n.link || '#'}" class="notification-action">Abrir Documento ➔</a>
                            </div>
                        </div>
                        ${n.lida ? '' : '<div class="unread-indicator"></div>'}
                    `;
                    dropdownEl.appendChild(item);
                });
            }
        }

        // Iniciar conexão WebSocket
        connectWebSocket();
    }
});
