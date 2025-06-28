document.getElementById('categorySearch').addEventListener('keyup', function () {
    const searchTerm = this.value.toLowerCase();
    const cards = document.querySelectorAll('.category-card');

    cards.forEach(card => {
      const name = card.querySelector('.category-name').textContent.toLowerCase();
      card.style.display = name.includes(searchTerm) ? 'block' : 'none';
    });
  });