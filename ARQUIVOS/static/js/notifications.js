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

            if (countBadge && countBadge.style.display !== 'none') {
                fetch(config.markReadUrl, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': config.csrfToken,
                        'Content-Type': 'application/json'
                    },
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'ok') {
                            countBadge.style.display = 'none';
                            // Informar WebSocket que as notificações foram lidas
                            if (window.notificationSocket && window.notificationSocket.readyState === WebSocket.OPEN) {
                                window.notificationSocket.send(JSON.stringify({ action: 'mark_read' }));
                            }
                        }
                    });
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
            novaNotificacao.innerHTML = `
                <a href="${link || '#'}">
                    ${mensagem}
                    <small style="display: block; color: #999; margin-top: 5px;">Agora mesmo</small>
                </a>
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
                    item.className = 'notification-item unread';
                    item.innerHTML = `
                        <a href="${n.link || '#'}">
                            ${n.mensagem}
                            <small style="display: block; color: #999; margin-top: 5px;">${n.data || ''}</small>
                        </a>
                    `;
                    dropdownEl.appendChild(item);
                });
            }
        }

        // Iniciar conexão WebSocket
        connectWebSocket();
    }
});
