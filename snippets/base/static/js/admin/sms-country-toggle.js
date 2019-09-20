(function () {
    function bindSMSCountry() {
        const chk_sms = document.querySelector('.form-row.field-include_sms input');
        const country_row = document.querySelector('.form-row.field-country');
        const country_input = document.querySelector('.form-row.field-country input');

        // make sure required fields exist
        if (chk_sms && country_input) {
            // get default value from input, falling back to 'us' if empty
            const country_default = country_input.value || 'us';
            
            function displayCountryField() {
                country_row.classList.add('visible');
            }

            function hideCountryField() {
                country_row.classList.remove('visible');
                
                // set the value back to default if user left it empty
                if (country_input.value === '') {
                    country_input.value = country_default;
                }
            }

            // on page load, determine if we should show the country field
            if (chk_sms.checked) {
                displayCountryField();
            }

            // toggle display of country field when SMS checkbox changes
            chk_sms.addEventListener('change', e => {
                if (chk_sms.checked) {
                    displayCountryField();
                } else {
                    hideCountryField();
                }
            });
        }
    }

    document.addEventListener('DOMContentLoaded', bindSMSCountry);
})();
