/* ═══════════════════════════════════════════════════════════
   Heka — main.js
   Requiere jQuery (cargado antes que este script en base.html)
   · Tema claro/oscuro (CLARO = predeterminado)
   · Timeout de sesión: aviso 9 min → cierre 10 min
   · Validación de formularios con jQuery
═══════════════════════════════════════════════════════════ */

/* ══════════════════════════════════════════
   1. TEMA — se ejecuta inmediatamente
══════════════════════════════════════════ */
(function () {
    // CLARO es el predeterminado si no hay preferencia guardada
    var saved = localStorage.getItem('heka-theme') || 'light';
    applyTheme(saved, false); // false = no animar en carga inicial

    function applyTheme(theme, animate) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('heka-theme', theme);

        var isDark  = theme === 'dark';
        var iconD   = document.getElementById('iconDark');
        var iconL   = document.getElementById('iconLight');
        var label   = document.getElementById('themeLabel');

        if (iconD)  iconD.style.display  = isDark ? 'block' : 'none';
        if (iconL)  iconL.style.display  = isDark ? 'none'  : 'block';
        if (label)  label.textContent    = isDark ? 'Modo claro' : 'Modo oscuro';
    }

    // Exponer para el botón
    window.hekaToggleTheme = function () {
        var cur = document.documentElement.getAttribute('data-theme') || 'light';
        applyTheme(cur === 'dark' ? 'light' : 'dark', true);
    };

    // Botón del topbar
    var btn = document.getElementById('themeToggle');
    if (btn) btn.addEventListener('click', window.hekaToggleTheme);
})();


/* ══════════════════════════════════════════
   Esperar a que jQuery esté disponible
══════════════════════════════════════════ */
$(function () {

    /* ══════════════════════════════════════════
       2. SESSION TIMEOUT
    ══════════════════════════════════════════ */
    var $warn = $('#session-warning');
    if ($warn.length) {
        var LOGOUT_URL = $warn.find('.sw-out').attr('href');
        var WARN_MS    = 9  * 60 * 1000;   // 9 min
        var OUT_MS     = 10 * 60 * 1000;   // 10 min
        var COUNT_SECS = 60;

        var warnT, outT, countI;

        function resetSession() {
            clearTimeout(warnT);
            clearTimeout(outT);
            clearInterval(countI);
            $warn.removeClass('show');

            warnT = setTimeout(showWarning, WARN_MS);
            outT  = setTimeout(function () {
                window.location.href = LOGOUT_URL;
            }, OUT_MS);
        }

        function showWarning() {
            var secs = COUNT_SECS;
            tick(secs);
            $warn.addClass('show');

            countI = setInterval(function () {
                secs--;
                tick(secs);
                if (secs <= 0) {
                    clearInterval(countI);
                    window.location.href = LOGOUT_URL;
                }
            }, 1000);
        }

        function tick(s) {
            $('#sw-timer').text(s + 's');
        }

        // Botón "Mantener sesión"
        $('#sw-keep-btn').on('click', function () {
            resetSession();
            // Ping silencioso al servidor para renovar sesión Django
            $.get(window.location.href);
        });

        // Cualquier actividad reinicia el timer
        $(document).on('mousemove keydown click scroll touchstart', function () {
            resetSession();
        });

        resetSession();
    }


    /* ══════════════════════════════════════════
       3. VALIDACIÓN DE FORMULARIOS CON JQUERY
       Se aplica a todos los <form> con class="validated-form"
       o automáticamente a forms con campos required
    ══════════════════════════════════════════ */

    // Reglas de validación por atributo o tipo
    var validators = {

        required: function ($el) {
            var val = $el.val();
            if ($el.is('select')) return val && val !== '';
            return $.trim(val) !== '';
        },

        email: function ($el) {
            return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test($.trim($el.val()));
        },

        minlength: function ($el) {
            var min = parseInt($el.attr('minlength') || $el.data('minlength'), 10);
            return $el.val().length >= min;
        },

        maxlength: function ($el) {
            var max = parseInt($el.attr('maxlength') || $el.data('maxlength'), 10);
            return $el.val().length <= max;
        },

        pattern: function ($el) {
            var pat = $el.attr('pattern');
            if (!pat) return true;
            return new RegExp('^(?:' + pat + ')$').test($el.val());
        },

        match: function ($el) {
            var target = $el.data('match');
            if (!target) return true;
            return $el.val() === $(target).val();
        },

        numeric: function ($el) {
            if (!$el.data('numeric')) return true;
            return /^\d+(\.\d+)?$/.test($.trim($el.val()));
        },

        // Sanitización: elimina tags HTML peligrosos del valor
        sanitize: function ($el) {
            var val = $el.val();
            // Elimina <script>, <iframe>, eventos on*, etc.
            var clean = val
                .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, '')
                .replace(/<iframe[\s\S]*?>[\s\S]*?<\/iframe>/gi, '')
                .replace(/on\w+\s*=\s*["'][^"']*["']/gi, '')
                .replace(/javascript:/gi, '');
            if (clean !== val) $el.val(clean);
            return true; // sanitize siempre pasa (ya limpió)
        }
    };

    var messages = {
        required:  'Este campo es obligatorio.',
        email:     'Ingresa un correo electrónico válido.',
        minlength: function ($el) {
            return 'Mínimo ' + ($el.attr('minlength') || $el.data('minlength')) + ' caracteres.';
        },
        maxlength: function ($el) {
            return 'Máximo ' + ($el.attr('maxlength') || $el.data('maxlength')) + ' caracteres.';
        },
        pattern:   'El formato no es válido.',
        match:     'Los valores no coinciden.',
        numeric:   'Solo se permiten números.'
    };

    function getMessage(rule, $el) {
        // Permite mensaje personalizado via data-msg-<regla>
        var custom = $el.data('msg-' + rule);
        if (custom) return custom;
        var msg = messages[rule];
        return typeof msg === 'function' ? msg($el) : (msg || 'Campo inválido.');
    }

    function validateField($el) {
        // Limpiar estado anterior
        $el.removeClass('is-invalid is-valid');
        $el.siblings('.field-error').remove();

        // Sanitizar primero siempre
        validators.sanitize($el);

        // Si está vacío y no es requerido, no validar más
        var isEmpty = $.trim($el.val()) === '' || ($el.is('select') && !$el.val());
        if (isEmpty && !$el.prop('required') && !$el.attr('required')) {
            return true;
        }

        var rules = ['required', 'email', 'minlength', 'maxlength', 'pattern', 'match', 'numeric'];
        var valid  = true;
        var firstError = '';

        for (var i = 0; i < rules.length; i++) {
            var rule = rules[i];
            var applicable = false;

            if (rule === 'required')   applicable = $el.prop('required') || !!$el.attr('required');
            if (rule === 'email')      applicable = $el.attr('type') === 'email';
            if (rule === 'minlength')  applicable = !!($el.attr('minlength') || $el.data('minlength'));
            if (rule === 'maxlength')  applicable = !!($el.attr('maxlength') || $el.data('maxlength'));
            if (rule === 'pattern')    applicable = !!$el.attr('pattern');
            if (rule === 'match')      applicable = !!$el.data('match');
            if (rule === 'numeric')    applicable = !!$el.data('numeric');

            if (applicable && !validators[rule]($el)) {
                valid = false;
                firstError = getMessage(rule, $el);
                break;
            }
        }

        if (!valid) {
            $el.addClass('is-invalid');
            $el.after('<span class="field-error">⚠ ' + firstError + '</span>');
        } else if ($.trim($el.val()) !== '') {
            $el.addClass('is-valid');
        }

        return valid;
    }

    // Validar campo al salir del foco
    $(document).on('blur', 'input.form-control, select.form-control, textarea.form-control', function () {
        validateField($(this));
    });

    // Limpiar error al escribir
    $(document).on('input change', 'input.form-control, select.form-control, textarea.form-control', function () {
        var $el = $(this);
        if ($el.hasClass('is-invalid')) {
            $el.removeClass('is-invalid');
            $el.siblings('.field-error').remove();
        }
    });

    // Interceptar submit de cualquier form que tenga campos form-control
    $(document).on('submit', 'form', function (e) {
        var $form  = $(this);
        var $fields = $form.find('input.form-control, select.form-control, textarea.form-control');
        if ($fields.length === 0) return; // form sin campos controlados: dejar pasar

        var formValid = true;
        $fields.each(function () {
            if (!validateField($(this))) {
                formValid = false;
            }
        });

        if (!formValid) {
            e.preventDefault();
            // Scroll al primer error
            var $first = $form.find('.is-invalid').first();
            if ($first.length) {
                $('html, body').animate({ scrollTop: $first.offset().top - 100 }, 300);
                $first.focus();
            }
        }
    });


    /* ══════════════════════════════════════════
       4. SEGURIDAD ADICIONAL
    ══════════════════════════════════════════ */

    // Deshabilitar botón submit tras envío para evitar doble click
    $(document).on('submit', 'form', function () {
        var $form = $(this);
        setTimeout(function () {
            $form.find('[type="submit"]').prop('disabled', true).css('opacity', '0.6');
        }, 0);
    });

    // Confirmar acciones destructivas en botones/links con data-confirm
    $(document).on('click', '[data-confirm]', function (e) {
        var msg = $(this).data('confirm') || '¿Estás seguro de realizar esta acción?';
        if (!confirm(msg)) {
            e.preventDefault();
            e.stopImmediatePropagation();
        }
    });

    // Auto-cerrar alertas después de 5 segundos
    setTimeout(function () {
        $('.alert').fadeOut(400, function () { $(this).remove(); });
    }, 5000);

}); // fin $(function)
