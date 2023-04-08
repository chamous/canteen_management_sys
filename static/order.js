// Get all the meal cards
const mealCards = document.querySelectorAll('.meal-card');

// Loop through each card and add a click event listener
mealCards.forEach(card => {
  const radioBtn = card.querySelector('input[type="radio"]');
  radioBtn.addEventListener('click', () => {
    // Reset border color for all cards
    mealCards.forEach(card => {
      card.querySelector('.meal-details').style.border = 'none';
    });
    // Set border color for selected card
    card.querySelector('.meal-details').style.border = '2px solid green';
  });
});
;
