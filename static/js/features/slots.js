/**
 * slots.js — Interactive hourly slot selection handler for booking interfaces.
 * States: available, hover, selected, booked.
 */
function initSlotPicker(options) {
    const counselorEl = document.getElementById(options.counselorInputId);
    const dateEl = document.getElementById(options.dateInputId);
    const containerEl = document.getElementById(options.slotsContainerId);
    const targetEl = document.getElementById(options.targetInputId);

    if (!counselorEl || !dateEl || !containerEl || !targetEl) return;

    async function loadSlots() {
        const counselorId = counselorEl.value;
        const dateStr = dateEl.value;

        if (!counselorId || !dateStr) {
            containerEl.innerHTML = '';
            return;
        }

        containerEl.innerHTML = '<div style="color: #64748b;">Loading available slots...</div>';

        try {
            const resp = await fetch(`/appointments/slots/?counselor_id=${counselorId}&date=${dateStr}`);
            const data = await resp.json();

            if (!resp.ok) {
                containerEl.innerHTML = `<div style="color: #ef4444;">${data.error || 'Failed to load slots.'}</div>`;
                return;
            }

            containerEl.innerHTML = '';
            if (!data.slots || data.slots.length === 0) {
                containerEl.innerHTML = '<div style="color: #64748b;">No available slots on this date.</div>';
                return;
            }

            data.slots.forEach(slot => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'btn btn-secondary btn-sm';
                btn.textContent = slot.formatted_time;
                btn.style.margin = '0.25rem';

                if (slot.is_available) {
                    btn.onclick = () => {
                        containerEl.querySelectorAll('button').forEach(b => {
                            if (!b.disabled) b.className = 'btn btn-secondary btn-sm';
                        });
                        btn.className = 'btn btn-primary btn-sm';
                        targetEl.value = slot.iso.slice(0, 16);
                    };
                } else {
                    btn.disabled = true;
                    btn.style.opacity = '0.5';
                    btn.style.cursor = 'not-allowed';
                    btn.title = slot.is_taken ? 'Already booked' : 'Past slot';
                }
                containerEl.appendChild(btn);
            });
        } catch (e) {
            containerEl.innerHTML = '<div style="color: #ef4444;">Availability lookup error.</div>';
        }
    }

    counselorEl.addEventListener('change', loadSlots);
    dateEl.addEventListener('change', loadSlots);
}
