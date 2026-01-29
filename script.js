document.addEventListener('DOMContentLoaded', () => {
  // Remove console logs as requested
  const outside = document.getElementById('view-outside');
  const inside = document.getElementById('view-inside');
  const enterBtn = document.getElementById('enter-btn');

  // Set initial view states
  outside.style.display = 'flex';
  outside.classList.add('active');
  outside.style.opacity = '1';
  inside.style.display = 'none';
  inside.classList.remove('active');
  inside.style.opacity = '0';

  // Hide all game screens
  document.querySelectorAll('.game-screen').forEach(s => {
    s.style.display = 'none';
    s.classList.remove('visible');
  });

  // Enter pub button handler
  enterBtn.addEventListener('click', () => {
    outside.style.opacity = '0';
    setTimeout(() => {
      outside.style.display = 'none';
      outside.classList.remove('active');
      inside.style.display = 'flex';
      inside.classList.add('active');
      inside.style.opacity = '1';
    }, 1200);
  });

  // Initialize Telegram WebApp
  if (window.Telegram?.WebApp) {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
  }

  // Show game screen function
  window.showGame = function(gameId) {
    inside.style.opacity = '0';
    setTimeout(() => {
      inside.style.display = 'none';
      inside.classList.remove('active');
      const screen = document.getElementById('game-' + gameId);
      if (!screen) return;
      screen.style.display = 'block';
      screen.classList.add('visible');
      screen.style.opacity = '1';
      if (gameId === 'football') loadFootballCard();
    }, 800);
  };

  // Back to pub function
  window.backToPub = function() {
    document.querySelectorAll('.game-screen').forEach(s => s.style.opacity = '0');
    setTimeout(() => {
      document.querySelectorAll('.game-screen').forEach(s => {
        s.style.display = 'none';
        s.classList.remove('visible');
      });
      inside.style.display = 'flex';
      inside.classList.add('active');
      inside.style.opacity = '1';
    }, 800);
  };

  // ========== FOOTBALL CARD ==========
  const footballTeams = [
    "Arsenal", "Ajax", "Bournemouth", "Brentford", "Brighton", "Burnley",
    "Chelsea", "Crystal Palace", "Everton", "Fulham", "Liverpool", "Luton",
    "Man City", "Man United", "Newcastle", "Nottingham Forest", "Sheffield Utd",
    "Tottenham", "West Ham", "Wolves", "Leicester", "Leeds", "Southampton",
    "Blackburn", "Birmingham", "Coventry", "Ipswich", "Middlesbrough", "Norwich",
    "Preston", "QPR", "Sheffield Wed"
  ];

  // Load football card grid
  function loadFootballCard() {
    const grid = document.getElementById('football-grid');
    if (!grid) return;

    grid.innerHTML = '';

    footballTeams.forEach(team => {
      const slot = document.createElement('div');
      slot.className = 'team-slot';
      slot.innerHTML = `
        <div class="team-name">${team}</div>
        <div class="username">[Pick Me]</div>
      `;
      slot.onclick = () => pickTeam(team, slot);
      grid.appendChild(slot);
    });

    // Load current state from bot
    loadCardState();
  }

  // Pick a team - sends to your bot
  function pickTeam(team, slot) {
    const user = Telegram.WebApp.initDataUnsafe.user;

    // Check if user has Telegram username
    if (!user || !user.username) {
      alert("You need a Telegram username to play. Please set one in Telegram settings.");
      return;
    }

    const username = '@' + user.username;

    // Confirm claim
    if (!confirm(`Claim ${team} for $1 USDC as ${username}?`)) {
      return;
    }

    // Visual feedback
    slot.style.opacity = '0.7';
    slot.querySelector('.username').textContent = 'Processing...';
    slot.style.pointerEvents = 'none';

    // Send to your bot - Use the action name your bot expects
    const claimData = {
      action: "pickteam_web",  // Changed to match bot handler
      team: team,
      username: username,
      user_id: user.id
    };

    try {
      Telegram.WebApp.sendData(JSON.stringify(claimData));

      // Request updated state after delay
      setTimeout(() => {
        Telegram.WebApp.sendData(JSON.stringify({
          action: "get_card_state"
        }));
      }, 2000);

    } catch (error) {
      alert("Error sending claim. Please try again.");

      // Reset slot on error
      slot.style.opacity = '1';
      slot.querySelector('.username').textContent = '[Pick Me]';
      slot.style.pointerEvents = 'auto';
    }
  }

  // Load current card state from bot
  function loadCardState() {
    Telegram.WebApp.sendData(JSON.stringify({
      action: "get_card_state"
    }));
  }

  // Update grid with claims from bot
  function updateGrid(claims) {
    const slots = document.querySelectorAll('.team-slot');

    slots.forEach(slot => {
      const team = slot.querySelector('.team-name').textContent.trim();
      const claimed = claims[team];

      if (claimed) {
        // Display the username (bot will send it)
        slot.querySelector('.username').textContent = claimed;
        slot.classList.add('claimed');
        slot.onclick = null;
        slot.style.opacity = '1';
        slot.style.pointerEvents = 'none';
      } else {
        // Reset any processing slots
        if (slot.style.opacity === '0.7') {
          slot.style.opacity = '1';
          slot.querySelector('.username').textContent = '[Pick Me]';
          slot.style.pointerEvents = 'auto';
        }
      }
    });
  }

  // Handle responses from bot
  Telegram.WebApp.onEvent('web_app_data', (event) => {
    const data = event.data;
    if (typeof data !== 'string') return;

    // Handle card state updates
    if (data.startsWith("CARD_STATE:")) {
      try {
        const json = data.replace('CARD_STATE:', '');
        const state = JSON.parse(json);

        // Check format - could be from your football_card.py
        if (state.teams && state.entries) {
          // Format from football_card.py - convert to simple {team: username}
          const simpleClaims = {};
          footballTeams.forEach(team => {
            if (state.entries[team]) {
              simpleClaims[team] = '@' + state.entries[team].username;
            } else {
              simpleClaims[team] = null;
            }
          });
          updateGrid(simpleClaims);
        } else if (typeof state === 'object') {
          // Simple format {team: username}
          updateGrid(state);
        }
      } catch (e) {
        // Silently fail - no console logs
      }
    }

    // Handle error messages from bot
    if (data.includes("CLAIM_DENIED") || data.includes("❌") || data.includes("No wallet")) {
      alert(data.replace("CLAIM_DENIED:", "").trim());

      // Reset all processing slots
      const slots = document.querySelectorAll('.team-slot');
      slots.forEach(slot => {
        if (slot.style.opacity === '0.7') {
          slot.style.opacity = '1';
          slot.querySelector('.username').textContent = '[Pick Me]';
          slot.style.pointerEvents = 'auto';
        }
      });
    }

    // Handle success messages
    if (data.includes("CLAIM_SUCCESS") || data.includes("✅")) {
      // Success! Grid will update with next CARD_STATE
    }
  });
});
