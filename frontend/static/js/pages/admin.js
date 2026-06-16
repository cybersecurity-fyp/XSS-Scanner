// XSSniper — Admin page logic

function _initAdmin() {
  if (!document.getElementById('user-mgmt-heading')) return;
  const tbody = document.querySelector('.data-table tbody');
  if (!tbody) return;
  tbody.addEventListener('click', e => {
    const btn = e.target.closest('[data-action="delete-user"]');
    if (btn) deleteUser(+btn.dataset.uid, btn.dataset.uname);
  });
}

document.addEventListener('DOMContentLoaded', _initAdmin);
document.addEventListener('htmx:afterSettle', _initAdmin);

async function deleteUser(userId, username) {
  const confirmed = await window.showConfirm(
    'Delete User',
    'Delete user "' + username + '"? This cannot be undone.',
    'Delete User'
  );
  if (!confirmed) return;
  try {
    await api('DELETE', '/api/v1/admin/users/' + userId);
    toast('User ' + username + ' deleted', 'success');
    document.getElementById('user-row-' + userId)?.remove();
  } catch (err) {
    toast(err.message, 'error');
  }
}
