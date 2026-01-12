(function ($) {
    'use strict';

    $(document).ready(function () {
        // Seletores para os campos
        // O autocomplete do Django usa Select2, então precisamos encontrar o elemento correto
        var admField = $('#id_administracao');
        var deptField = $('#id_departamento');
        var secField = $('#id_seccao');

        // Função para obter o valor da administração (funciona com Select2 ou select normal)
        function getAdministracaoId() {
            // Primeiro tenta o select normal
            if (admField.length && admField.val()) {
                return admField.val();
            }
            // Se for Select2, o valor está no elemento original
            var select2Data = admField.select2 ? admField.select2('data') : null;
            if (select2Data && select2Data.length > 0) {
                return select2Data[0].id;
            }
            return null;
        }

        // --- Função: Carregar Departamentos ---
        function loadDepartamentos(admId) {
            console.log('Carregando departamentos para administração:', admId);

            if (!admId) {
                deptField.html('<option value="">---------</option>');
                secField.html('<option value="">---------</option>');
                return;
            }

            $.ajax({
                url: '/ajax/load-departamentos/',
                data: { 'administracao': admId },
                success: function (data) {
                    console.log('Departamentos carregados com sucesso');
                    deptField.html(data);
                    secField.html('<option value="">---------</option>');
                },
                error: function (xhr, status, error) {
                    console.error('Erro ao carregar departamentos:', error);
                }
            });
        }

        // --- Função: Carregar Secções ---
        function loadSeccoes(deptId) {
            console.log('Carregando secções para departamento:', deptId);

            if (!deptId) {
                secField.html('<option value="">---------</option>');
                return;
            }

            $.ajax({
                url: '/ajax/load-seccoes/',
                data: { 'departamento': deptId },
                success: function (data) {
                    console.log('Secções carregadas com sucesso');
                    secField.html(data);
                },
                error: function (xhr, status, error) {
                    console.error('Erro ao carregar secções:', error);
                }
            });
        }

        // --- Event Listeners ---

        // Para Select normal
        admField.on('change', function () {
            var admId = $(this).val();
            console.log('Administração alterada (change):', admId);
            loadDepartamentos(admId);
        });

        // Para Select2 (autocomplete do Django)
        admField.on('select2:select', function (e) {
            var admId = e.params.data.id;
            console.log('Administração alterada (select2):', admId);
            loadDepartamentos(admId);
        });

        // Quando limpa o Select2
        admField.on('select2:clear', function () {
            console.log('Administração limpa');
            deptField.html('<option value="">---------</option>');
            secField.html('<option value="">---------</option>');
        });

        // Departamento change
        deptField.on('change', function () {
            var deptId = $(this).val();
            console.log('Departamento alterado:', deptId);
            loadSeccoes(deptId);
        });
    });
})(django.jQuery);
