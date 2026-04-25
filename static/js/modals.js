function showDeleteModal(itemType, onConfirm) {
    document.getElementById('delete-item-type').textContent = itemType;
    document.getElementById('delete-confirm-btn').onclick = function() { eval(onConfirm); };
    document.getElementById('delete-modal').classList.remove('hidden');
}

function closeDeleteModal() {
    document.getElementById('delete-modal').classList.add('hidden');
}
