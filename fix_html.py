with open(r'c:\Users\User\OneDrive - iitr.ac.in\project_01\web_v1\templates\marketplace\experience_detail_v3.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open(r'c:\Users\User\OneDrive - iitr.ac.in\project_01\web_v1\templates\marketplace\experience_detail_v3.html', 'w', encoding='utf-8') as f:
    f.writelines(lines[:334])
    f.write('''{% endblock %}

{% block extra_js %}
<script>
    const startDateEl = document.getElementById('start_date');
    const endDateEl = document.getElementById('end_date');
    const guestsEl = document.getElementById('guests');
    const pricePreviewContainer = document.getElementById('price_preview_container');
    const previewGuests = document.getElementById('preview_guests');
    const previewDays = document.getElementById('preview_days');
    const previewCalculation = document.getElementById('preview_calculation');
    const previewTotal = document.getElementById('preview_total');
    const pricePerPerson = parseFloat("{{ listing.price_per_person }}");

    function calculateTotal() {
        if (startDateEl && endDateEl && startDateEl.value && endDateEl.value && guestsEl && guestsEl.value) {
            const start = new Date(startDateEl.value);
            const end = new Date(endDateEl.value);

            start.setHours(0, 0, 0, 0);
            end.setHours(0, 0, 0, 0);

            const days = Math.round((end - start) / (1000 * 60 * 60 * 24));

            if (days > 0) {
                const guests = parseInt(guestsEl.value);
                const total = days * pricePerPerson * guests;

                if(previewGuests) previewGuests.innerText = guests;
                if(previewDays) previewDays.innerText = days;
                if(previewCalculation) previewCalculation.innerText = "₹" + total.toLocaleString('en-IN');
                if(previewTotal) previewTotal.innerText = "₹" + total.toLocaleString('en-IN');
                if(pricePreviewContainer) pricePreviewContainer.classList.remove('d-none');
            } else {
                if(pricePreviewContainer) pricePreviewContainer.classList.add('d-none');
            }
        } else {
            if(pricePreviewContainer) pricePreviewContainer.classList.add('d-none');
        }
    }

    if (startDateEl) {
        const today = new Date().toISOString().split('T')[0];
        startDateEl.setAttribute('min', today);
        startDateEl.addEventListener('change', function () {
            if (endDateEl) endDateEl.setAttribute('min', this.value);
            calculateTotal();
        });
    }

    if (endDateEl) endDateEl.addEventListener('change', calculateTotal);
    if (guestsEl) guestsEl.addEventListener('change', calculateTotal);
</script>
{% endblock %}
''')
