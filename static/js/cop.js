/**
 * Formateo en tiempo real de Pesos Colombianos (COP).
 * Entrada/salida: "$ 1.200.000" (sin decimales)
 */
function parseCOP(valor) {
    if (!valor) return 0;
    const limpio = String(valor).replace(/\$/g, '').replace(/\./g, '').replace(/,/g, '').trim();
    const n = parseInt(limpio, 10);
    return isNaN(n) ? 0 : n;
}

function formatCOP(num) {
    const n = Math.abs(Math.round(num || 0));
    const texto = n.toLocaleString('es-CO').replace(/,/g, '.');
    return (num < 0 ? '-$ ' : '$ ') + texto;
}

function initCOPInputs() {
    document.querySelectorAll('[data-cop="true"], .input-cop').forEach(input => {
        if (input.dataset.copInit) return;
        input.dataset.copInit = '1';

        input.addEventListener('input', function () {
            const raw = this.value.replace(/[^\d]/g, '');
            if (raw === '') {
                this.value = '';
                return;
            }
            this.value = formatCOP(parseInt(raw, 10));
            this.setSelectionRange(this.value.length, this.value.length);
        });

        input.addEventListener('blur', function () {
            const val = parseCOP(this.value);
            this.value = val > 0 ? formatCOP(val) : '';
        });

        if (input.value && !input.value.includes('$')) {
            const val = parseCOP(input.value);
            if (val > 0) input.value = formatCOP(val);
        }
    });
}

document.addEventListener('DOMContentLoaded', initCOPInputs);

function setInversionPlazo(meses) {
    const input = document.getElementById('id_fecha_vencimiento');
    if (!input) return;
    const hoy = new Date();
    hoy.setMonth(hoy.getMonth() + meses);
    input.value = hoy.toISOString().split('T')[0];
}

function toggleExtenderInversion() {
    const extender = document.getElementById('id_extender');
    const montoFinal = document.getElementById('id_monto_final');
    const nuevaFecha = document.getElementById('id_nueva_fecha');
    if (!extender) return;
    const bloqueMonto = montoFinal?.closest('.campo-monto-final');
    const bloqueFecha = nuevaFecha?.closest('.campo-nueva-fecha');
    if (extender.checked) {
        bloqueMonto?.classList.add('hidden');
        bloqueFecha?.classList.remove('hidden');
        if (montoFinal) montoFinal.required = false;
        if (nuevaFecha) nuevaFecha.required = true;
    } else {
        bloqueMonto?.classList.remove('hidden');
        bloqueFecha?.classList.add('hidden');
        if (montoFinal) montoFinal.required = true;
        if (nuevaFecha) nuevaFecha.required = false;
    }
}

function toggleEnvioAhorro() {
    const check = document.getElementById('id_es_envio_ahorro');
    const cat = document.getElementById('id_categoria');
    const bloqueCat = cat?.closest('.campo-categoria');
    if (!check || !bloqueCat) return;
    if (check.checked) {
        bloqueCat.classList.add('opacity-40', 'pointer-events-none');
        if (cat) cat.required = false;
    } else {
        bloqueCat.classList.remove('opacity-40', 'pointer-events-none');
        if (cat) cat.required = true;
    }
}

function initPieChart(canvasId, labels, data, colors) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !labels.length) return;
    new Chart(canvas, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: '#fff',
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom' },
                tooltip: {
                    callbacks: {
                        label: function(ctx) {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = ((ctx.raw / total) * 100).toFixed(1);
                            return ctx.label + ': ' + formatCOP(ctx.raw) + ' (' + pct + '%)';
                        }
                    }
                }
            }
        }
    });
}
