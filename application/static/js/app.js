const $ = (selector) => document.querySelector(selector);

// HTML is rendered by Django. JavaScript only enhances forms and dialogs.
function openDialog(title, message) {
    $('#dialog-title').textContent = title;
    $('#dialog-text').textContent = message;
    $('#dialog').showModal();
}

const dialogContent = {
    rules: ['Правила акции', `Период акции: ${document.body.dataset.promoStart} — ${document.body.dataset.promoEnd}.\nМинимальная сумма покупки — 1 000 ₽. Каждый чек можно зарегистрировать один раз.`],
    profile: ['Профиль', 'Елена Иванова\nnameuser@email.com'],
    notifications: ['Уведомления', 'Новых уведомлений пока нет.'],
};

document.querySelectorAll('[data-dialog]').forEach(button => {
    button.addEventListener('click', () => openDialog(...dialogContent[button.dataset.dialog]));
});
document.querySelectorAll('[data-message]').forEach(button => {
    button.addEventListener('click', () => openDialog(button.dataset.title, button.dataset.message));
});
$('#dialog-close').addEventListener('click', () => $('#dialog').close());
$('#dialog').addEventListener('click', event => {
    if (event.target !== $('#dialog')) return;
    const rect = event.target.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) {
        event.target.close();
    }
});

function validate(input){const value=input.value.trim();let error='';if(!value)error='Заполните это поле';else if(input.name==='fn'&&!/^\d{16}$/.test(value))error='ФН должен содержать 16 цифр';else if(input.name==='fd'&&!/^\d{1,10}$/.test(value))error='Введите номер чека: от 1 до 10 цифр';else if(input.name==='fp'&&!/^\d{1,10}$/.test(value))error='ФП должен содержать от 1 до 10 цифр';else if(input.name==='amount'&&(!/^\d+(?:[.,]\d{1,2})?$/.test(value)||Number(value.replace(',','.'))<1000))error='Введите сумму от 1 000 ₽, не более двух знаков после запятой';else if(input.name==='purchased'&&Number.isNaN(new Date(value).getTime()))error='Введите корректные дату и время';input.setAttribute('aria-invalid',Boolean(error));$('#'+input.name+'-error').textContent=error;return !error;}

const form = $('#receipt-form');
if (form) {
    form.addEventListener('submit', event => {
        const inputs = [...form.querySelectorAll('input:not([type="hidden"])')];
        const results = inputs.map(validate);
        if (results.includes(false)) {
            event.preventDefault();
            inputs[results.indexOf(false)].focus();
        }
        // A valid form uses its normal HTML POST action.
    });
    form.querySelectorAll('input:not([type="hidden"])').forEach(input => {
        input.addEventListener('input', () => {
            if (input.getAttribute('aria-invalid') === 'true') validate(input);
        });
    });
}
