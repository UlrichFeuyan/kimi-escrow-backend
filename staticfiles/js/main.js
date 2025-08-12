const KimiEscrow = {
apiBaseUrl: '/api',
csrfToken: document.querySelector('[name=csrfmiddlewaretoken]')?.value || csrfToken,
currentUser: window.currentUser || null,
endpoints: {
auth: {
login: '/api/auth/login/',
logout: '/api/auth/logout/',
register: '/api/auth/register/',
profile: '/api/auth/profile/',
verifyPhone: '/api/auth/verify-phone/',
changePassword: '/api/auth/change-password/'
},
escrow: {
transactions: '/api/escrow/transactions/',
transactionDetail: (id) => `/api/escrow/transactions/${id}/`,
transactionActions: (id) => `/api/escrow/transactions/${id}/actions/`,
transactionMessages: (id) => `/api/escrow/transactions/${id}/messages/`,
statistics: '/api/escrow/statistics/'
},
payments: {
collect: '/api/payments/momo/collect/',
status: (ref) => `/api/payments/momo/status/${ref}/`,
history: '/api/payments/history/',
methods: '/api/payments/methods/'
},
disputes: {
list: '/api/disputes/',
detail: (id) => `/api/disputes/${id}/`,
evidence: (id) => `/api/disputes/${id}/evidence/`,
comments: (id) => `/api/disputes/${id}/comments/`,
assign: (id) => `/api/disputes/${id}/assign/`,
resolve: (id) => `/api/disputes/${id}/resolve/`
},
admin: {
users: '/api/auth/admin/users/',
userDetail: (id) => `/api/auth/admin/users/${id}/`,
kycApprove: (userId) => `/api/auth/admin/kyc/${userId}/approve/`,
auditLogs: '/api/core/audit-logs/'
}
}
};
async function apiRequest(url, options = {}) {
const defaultOptions = {
method: 'GET',
headers: {
'Content-Type': 'application/json',
'X-CSRFToken': KimiEscrow.csrfToken
},
credentials: 'include'
};
const token = localStorage.getItem('access_token');
if (token) {
defaultOptions.headers['Authorization'] = `Bearer ${token}`;
}
const config = { ...defaultOptions, ...options };
if (options.headers) {
config.headers = { ...defaultOptions.headers, ...options.headers };
}
try {
showLoadingSpinner();
const response = await fetch(url, config);
const data = await response.json();
if (!response.ok) {
throw new Error(data.message || `HTTP error! status: ${response.status}`);
}
return data;
} catch (error) {
console.error('API Request Error:', error);
showAlert('Erreur de connexion: ' + error.message, 'danger');
throw error;
} finally {
hideLoadingSpinner();
}
}
function showLoadingSpinner() {
const spinner = document.getElementById('loading-spinner');
if (spinner) {
spinner.classList.remove('d-none');
}
}
function hideLoadingSpinner() {
const spinner = document.getElementById('loading-spinner');
if (spinner) {
spinner.classList.add('d-none');
}
}
function showAlert(message, type = 'info', duration = 5000) {
const alertHtml = `
<div class="alert alert-${type} alert-dismissible fade show" role="alert">
<i class="bi bi-${getAlertIcon(type)}"></i>
${message}
<button type="button" class="btn-close" data-bs-dismiss="alert"></button>
</div>
`;
const container = document.querySelector('.container:first-of-type') || document.body;
const alertDiv = document.createElement('div');
alertDiv.innerHTML = alertHtml;
container.insertBefore(alertDiv.firstElementChild, container.firstElementChild);
if (duration > 0) {
setTimeout(() => {
const alert = document.querySelector('.alert');
if (alert) {
const bsAlert = new bootstrap.Alert(alert);
bsAlert.close();
}
}, duration);
}
}
function getAlertIcon(type) {
const icons = {
'success': 'check-circle',
'danger': 'exclamation-triangle',
'warning': 'exclamation-circle',
'info': 'info-circle'
};
return icons[type] || 'info-circle';
}
function formatAmount(amount) {
return new Intl.NumberFormat('fr-FR', {
style: 'currency',
currency: 'XAF',
minimumFractionDigits: 0
}).format(amount);
}
function formatDate(dateString) {
return new Date(dateString).toLocaleDateString('fr-FR', {
year: 'numeric',
month: 'long',
day: 'numeric',
hour: '2-digit',
minute: '2-digit'
});
}
function getStatusBadge(status) {
const statusMap = {
'PENDING': { class: 'warning', text: 'En attente' },
'PAYMENT_PENDING': { class: 'warning', text: 'Paiement en attente' },
'PAYMENT_CONFIRMED': { class: 'info', text: 'Paiement confirmé' },
'DELIVERED': { class: 'primary', text: 'Livré' },
'COMPLETED': { class: 'success', text: 'Terminé' },
'CANCELLED': { class: 'secondary', text: 'Annulé' },
'DISPUTED': { class: 'danger', text: 'En litige' }
};
const statusInfo = statusMap[status] || { class: 'secondary', text: status };
return `<span class="badge bg-${statusInfo.class}">${statusInfo.text}</span>`;
}
async function loadTransactions(filters = {}) {
try {
const queryParams = new URLSearchParams(filters).toString();
const url = `${KimiEscrow.endpoints.escrow.transactions}${queryParams ? '?' + queryParams : ''}`;
const response = await apiRequest(url);
if (response.success) {
displayTransactions(response.data.results);
updatePagination(response.data);
}
} catch (error) {
showAlert('Erreur lors du chargement des transactions', 'danger');
}
}
function displayTransactions(transactions) {
const container = document.getElementById('transactions-list');
if (!container) return;
if (transactions.length === 0) {
container.innerHTML = `
<div class="text-center py-5">
<i class="bi bi-inbox display-1 text-muted"></i>
<h4 class="mt-3">Aucune transaction</h4>
<p class="text-muted">Vous n'avez pas encore de transactions.</p>
</div>
`;
return;
}
const html = transactions.map(transaction => `
<div class="card mb-3 transaction-card" data-id="${transaction.id}">
<div class="card-body">
<div class="row align-items-center">
<div class="col-md-8">
<h5 class="card-title mb-1">${transaction.title}</h5>
<p class="card-text text-muted mb-2">${transaction.description}</p>
<div class="d-flex align-items-center">
<span class="me-3">
<i class="bi bi-cash"></i>
<strong>${formatAmount(transaction.amount)}</strong>
</span>
<span class="me-3">
<i class="bi bi-calendar"></i>
${formatDate(transaction.created_at)}
</span>
${getStatusBadge(transaction.status)}
</div>
</div>
<div class="col-md-4 text-md-end">
<div class="btn-group" role="group">
<a href="/escrow/transaction/${transaction.id}/" class="btn btn-outline-primary btn-sm">
<i class="bi bi-eye"></i> Voir
</a>
${getTransactionActions(transaction)}
</div>
</div>
</div>
</div>
</div>
`).join('');
container.innerHTML = html;
}
function getTransactionActions(transaction) {
const actions = [];
const userRole = KimiEscrow.currentUser?.role;
if (userRole === 'BUYER') {
if (transaction.status === 'PENDING') {
actions.push(`<button class="btn btn-success btn-sm" onclick="payTransaction(${transaction.id})">
<i class="bi bi-credit-card"></i> Payer
</button>`);
}
if (transaction.status === 'DELIVERED') {
actions.push(`<button class="btn btn-success btn-sm" onclick="confirmDelivery(${transaction.id})">
<i class="bi bi-check-circle"></i> Confirmer
</button>`);
}
if (['DELIVERED', 'PAYMENT_CONFIRMED'].includes(transaction.status)) {
actions.push(`<button class="btn btn-warning btn-sm" onclick="openDispute(${transaction.id})">
<i class="bi bi-exclamation-triangle"></i> Litige
</button>`);
}
} else if (userRole === 'SELLER') {
if (transaction.status === 'PAYMENT_CONFIRMED') {
actions.push(`<button class="btn btn-primary btn-sm" onclick="markAsDelivered(${transaction.id})">
<i class="bi bi-truck"></i> Marquer livré
</button>`);
}
}
return actions.join('');
}
async function performTransactionAction(transactionId, action, data = {}) {
try {
const url = KimiEscrow.endpoints.escrow.transactionActions(transactionId);
const response = await apiRequest(url, {
method: 'POST',
body: JSON.stringify({ action, ...data })
});
if (response.success) {
showAlert(response.message, 'success');
loadTransactions(); 
}
} catch (error) {
showAlert('Erreur lors de l\'action sur la transaction', 'danger');
}
}
function markAsDelivered(transactionId) {
const notes = prompt('Notes sur la livraison (optionnel):');
performTransactionAction(transactionId, 'mark_delivered', { notes });
}
function confirmDelivery(transactionId) {
if (confirm('Confirmer que vous avez bien reçu le produit/service ?')) {
const notes = prompt('Commentaire sur la réception (optionnel):');
performTransactionAction(transactionId, 'confirm_delivery', { notes });
}
}
function openDispute(transactionId) {
window.location.href = `/disputes/create/?transaction=${transactionId}`;
}
async function payTransaction(transactionId) {
try {
const transactionResponse = await apiRequest(KimiEscrow.endpoints.escrow.transactionDetail(transactionId));
const transaction = transactionResponse.data;
showPaymentModal(transaction);
} catch (error) {
showAlert('Erreur lors de l\'initialisation du paiement', 'danger');
}
}
function showPaymentModal(transaction) {
const modalHtml = `
<div class="modal fade" id="paymentModal" tabindex="-1">
<div class="modal-dialog">
<div class="modal-content">
<div class="modal-header">
<h5 class="modal-title">Paiement - ${transaction.title}</h5>
<button type="button" class="btn-close" data-bs-dismiss="modal"></button>
</div>
<div class="modal-body">
<div class="mb-3">
<strong>Montant à payer:</strong> ${formatAmount(transaction.amount)}
</div>
<form id="paymentForm">
<div class="mb-3">
<label class="form-label">Numéro de téléphone</label>
<input type="tel" class="form-control" id="phoneNumber" 
value="${KimiEscrow.currentUser?.phone_number || ''}" required>
</div>
<div class="mb-3">
<label class="form-label">Méthode de paiement</label>
<select class="form-select" id="paymentProvider" required>
<option value="">Choisir...</option>
<option value="MTN_MOMO">MTN Mobile Money</option>
<option value="ORANGE_MONEY">Orange Money</option>
</select>
</div>
<div class="alert alert-info">
<i class="bi bi-info-circle me-2"></i>
Vous recevrez un SMS pour confirmer le paiement.
</div>
</form>
</div>
<div class="modal-footer">
<button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annuler</button>
<button type="button" class="btn btn-primary" onclick="processPayment(${transaction.id})">
<i class="bi bi-credit-card me-2"></i>Payer ${formatAmount(transaction.amount)}
</button>
</div>
</div>
</div>
</div>
`;
const existingModal = document.getElementById('paymentModal');
if (existingModal) {
existingModal.remove();
}
document.body.insertAdjacentHTML('beforeend', modalHtml);
const modal = new bootstrap.Modal(document.getElementById('paymentModal'));
modal.show();
}
async function processPayment(transactionId) {
const form = document.getElementById('paymentForm');
const phoneNumber = form.querySelector('#phoneNumber').value;
const provider = form.querySelector('#paymentProvider').value;
if (!phoneNumber || !provider) {
showAlert('Veuillez remplir tous les champs', 'warning');
return;
}
try {
const transactionResponse = await apiRequest(KimiEscrow.endpoints.escrow.transactionDetail(transactionId));
const transaction = transactionResponse.data;
const paymentData = {
transaction_id: transactionId,
phone_number: phoneNumber,
provider: provider,
amount: transaction.amount
};
const response = await apiRequest(KimiEscrow.endpoints.payments.collect, {
method: 'POST',
body: JSON.stringify(paymentData)
});
if (response.success) {
const modal = bootstrap.Modal.getInstance(document.getElementById('paymentModal'));
modal.hide();
showAlert('Paiement initié! Vérifiez votre téléphone pour confirmer.', 'success');
showPaymentStatusModal(response.data.reference);
}
} catch (error) {
showAlert('Erreur lors du paiement: ' + error.message, 'danger');
}
}
function showPaymentStatusModal(paymentReference) {
const modalHtml = `
<div class="modal fade" id="paymentStatusModal" tabindex="-1">
<div class="modal-dialog">
<div class="modal-content">
<div class="modal-header">
<h5 class="modal-title">Suivi du paiement</h5>
<button type="button" class="btn-close" data-bs-dismiss="modal"></button>
</div>
<div class="modal-body text-center">
<div class="spinner-border text-primary mb-3" role="status">
<span class="visually-hidden">Vérification...</span>
</div>
<h6>Vérification du paiement en cours...</h6>
<p class="text-muted">Référence: ${paymentReference}</p>
<div id="paymentStatusContent">
<p>Veuillez confirmer le paiement sur votre téléphone.</p>
</div>
</div>
<div class="modal-footer">
<button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fermer</button>
</div>
</div>
</div>
</div>
`;
document.body.insertAdjacentHTML('beforeend', modalHtml);
const modal = new bootstrap.Modal(document.getElementById('paymentStatusModal'));
modal.show();
checkPaymentStatus(paymentReference);
}
async function checkPaymentStatus(paymentReference, attempts = 0) {
const maxAttempts = 20; 
if (attempts >= maxAttempts) {
document.getElementById('paymentStatusContent').innerHTML = `
<div class="alert alert-warning">
<i class="bi bi-clock me-2"></i>
Le paiement prend plus de temps que prévu. Vous pouvez fermer cette fenêtre et vérifier plus tard.
</div>
`;
return;
}
try {
const response = await apiRequest(KimiEscrow.endpoints.payments.status(paymentReference));
if (response.success) {
const payment = response.data;
if (payment.status === 'COMPLETED') {
document.getElementById('paymentStatusContent').innerHTML = `
<div class="alert alert-success">
<i class="bi bi-check-circle me-2"></i>
Paiement confirmé! La transaction va être mise à jour.
</div>
`;
setTimeout(() => {
const modal = bootstrap.Modal.getInstance(document.getElementById('paymentStatusModal'));
modal.hide();
loadTransactions(); 
}, 2000);
} else if (payment.status === 'FAILED') {
document.getElementById('paymentStatusContent').innerHTML = `
<div class="alert alert-danger">
<i class="bi bi-x-circle me-2"></i>
Paiement échoué. Veuillez réessayer.
</div>
`;
} else {
setTimeout(() => checkPaymentStatus(paymentReference, attempts + 1), 6000);
}
}
} catch (error) {
console.error('Erreur vérification paiement:', error);
setTimeout(() => checkPaymentStatus(paymentReference, attempts + 1), 6000);
}
}
function initFileUpload() {
const fileAreas = document.querySelectorAll('.file-upload-area');
fileAreas.forEach(area => {
const input = area.querySelector('input[type="file"]');
const preview = area.querySelector('.file-preview');
area.addEventListener('click', () => input.click());
area.addEventListener('dragover', (e) => {
e.preventDefault();
area.classList.add('dragover');
});
area.addEventListener('dragleave', () => {
area.classList.remove('dragover');
});
area.addEventListener('drop', (e) => {
e.preventDefault();
area.classList.remove('dragover');
const files = e.dataTransfer.files;
if (files.length > 0) {
input.files = files;
handleFileSelect(input, area, preview);
}
});
input.addEventListener('change', () => {
handleFileSelect(input, area, preview);
});
});
}
function handleFileSelect(input, area, preview) {
const file = input.files[0];
if (!file) return;
const allowedTypes = input.accept ? input.accept.split(',').map(t => t.trim()) : [];
if (allowedTypes.length > 0 && !allowedTypes.some(type => file.type.match(type))) {
showAlert('Type de fichier non autorisé', 'warning');
return;
}
if (file.size > 5 * 1024 * 1024) {
showAlert('Le fichier est trop volumineux (max 5MB)', 'warning');
return;
}
area.classList.add('has-file');
if (file.type.startsWith('image/') && preview) {
const reader = new FileReader();
reader.onload = (e) => {
preview.src = e.target.result;
preview.style.display = 'block';
};
reader.readAsDataURL(file);
}
const textElement = area.querySelector('.upload-text');
if (textElement) {
textElement.textContent = file.name;
}
}
async function loadNotifications() {
try {
const notifications = [
{
id: 1,
title: 'Nouveau paiement reçu',
message: 'Vous avez reçu un paiement de 150,000 FCFA',
type: 'success',
read: false,
timestamp: new Date().toISOString()
}
];
displayNotifications(notifications);
updateNotificationBadge(notifications.filter(n => !n.read).length);
} catch (error) {
console.error('Erreur chargement notifications:', error);
}
}
function displayNotifications(notifications) {
const container = document.getElementById('notifications-list');
const noNotifications = document.getElementById('no-notifications');
if (!container) return;
if (notifications.length === 0) {
noNotifications.style.display = 'block';
return;
}
noNotifications.style.display = 'none';
const html = notifications.map(notification => `
<li class="notification-item ${!notification.read ? 'unread' : ''}" data-id="${notification.id}">
<div class="d-flex">
<div class="flex-grow-1">
<h6 class="mb-1">${notification.title}</h6>
<p class="mb-1 small">${notification.message}</p>
<small class="text-muted">${formatDate(notification.timestamp)}</small>
</div>
${!notification.read ? '<div class="ms-2"><span class="badge bg-primary"></span></div>' : ''}
</div>
</li>
`).join('');
container.innerHTML = html;
}
function updateNotificationBadge(count) {
const badge = document.getElementById('notification-count');
if (!badge) return;
if (count > 0) {
badge.textContent = count > 99 ? '99+' : count;
badge.style.display = 'block';
} else {
badge.style.display = 'none';
}
}
document.addEventListener('DOMContentLoaded', function() {
initFileUpload();
if (KimiEscrow.currentUser?.isAuthenticated) {
loadNotifications();
setInterval(loadNotifications, 30000);
}
initAjaxForms();
initFilters();
const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
tooltips.forEach(tooltip => new bootstrap.Tooltip(tooltip));
const popovers = document.querySelectorAll('[data-bs-toggle="popover"]');
popovers.forEach(popover => new bootstrap.Popover(popover));
});
function initAjaxForms() {
const ajaxForms = document.querySelectorAll('.ajax-form');
ajaxForms.forEach(form => {
form.addEventListener('submit', async function(e) {
e.preventDefault();
const formData = new FormData(form);
const url = form.action;
const method = form.method || 'POST';
try {
const response = await apiRequest(url, {
method: method.toUpperCase(),
body: formData,
headers: {} 
});
if (response.success) {
showAlert(response.message || 'Action effectuée avec succès', 'success');
const redirect = form.dataset.redirect;
if (redirect) {
window.location.href = redirect;
} else {
location.reload();
}
}
} catch (error) {
showAlert('Erreur lors de l\'envoi: ' + error.message, 'danger');
}
});
});
}
function initFilters() {
const statusFilters = document.querySelectorAll('.status-filter');
statusFilters.forEach(filter => {
filter.addEventListener('change', function() {
const filters = { status: this.value };
loadTransactions(filters);
});
});
const searchInput = document.getElementById('search-input');
if (searchInput) {
let searchTimeout;
searchInput.addEventListener('input', function() {
clearTimeout(searchTimeout);
searchTimeout = setTimeout(() => {
const filters = { search: this.value };
loadTransactions(filters);
}, 500);
});
}
}
function updatePagination(data) {
const paginationContainer = document.getElementById('pagination-container');
if (!paginationContainer || !data.next && !data.previous) {
if (paginationContainer) paginationContainer.innerHTML = '';
return;
}
const currentPage = Math.ceil(data.count / (data.results?.length || 10));
const totalPages = Math.ceil(data.count / 10); 
let paginationHtml = '<nav><ul class="pagination justify-content-center">';
if (data.previous) {
paginationHtml += `<li class="page-item">
<a class="page-link" href="#" onclick="loadPage('${data.previous}')">Précédent</a>
</li>`;
}
for (let i = Math.max(1, currentPage - 2); i <= Math.min(totalPages, currentPage + 2); i++) {
paginationHtml += `<li class="page-item ${i === currentPage ? 'active' : ''}">
<a class="page-link" href="#" onclick="loadPage(${i})">${i}</a>
</li>`;
}
if (data.next) {
paginationHtml += `<li class="page-item">
<a class="page-link" href="#" onclick="loadPage('${data.next}')">Suivant</a>
</li>`;
}
paginationHtml += '</ul></nav>';
paginationContainer.innerHTML = paginationHtml;
}
async function loadPage(page) {
let url;
if (typeof page === 'string' && page.startsWith('http')) {
url = page;
} else {
url = `${KimiEscrow.endpoints.escrow.transactions}?page=${page}`;
}
try {
const response = await apiRequest(url);
if (response.success) {
displayTransactions(response.data.results);
updatePagination(response.data);
}
} catch (error) {
showAlert('Erreur lors du chargement de la page', 'danger');
}
}
window.KimiEscrow = KimiEscrow;
window.loadTransactions = loadTransactions;
window.payTransaction = payTransaction;
window.markAsDelivered = markAsDelivered;
window.confirmDelivery = confirmDelivery;
window.openDispute = openDispute;
window.processPayment = processPayment;
window.loadPage = loadPage;