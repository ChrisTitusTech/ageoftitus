const channelName = 'TitusTechGaming';
const clientId = 'au9081y3ft41wtb1p4im5502qy5emu';

// Move this inside the function to ensure the element exists when the script runs
// const twitchEmbedElement = document.getElementById('twitch-embed');

function checkLiveStatus() {
  const twitchEmbedElement = document.getElementById('twitch-embed');
  
  if (!twitchEmbedElement) {
    console.error('Twitch embed element not found');
    return;
  }

  // Fetch the Bearer token from a file or environment variable
  fetch('/path/to/bearer-token.txt')
    .then(response => response.text())
    .then(bearerToken => {
      return fetch(`https://api.twitch.tv/helix/streams?user_login=${channelName}`, {
        headers: {
          'Client-ID': clientId,
          'Authorization': `Bearer ${bearerToken.trim()}`
        }
      });
    })
    .then(response => response.json())
    .then(data => {
      if (data.data && data.data.length > 0) {
        // Channel is live
        twitchEmbedElement.innerHTML = `
          <iframe
            src="https://player.twitch.tv/?channel=${channelName}&parent=${window.location.hostname}"
            height="480"
            width="100%"
            allowfullscreen>
          </iframe>
        `;
      } else {
        // Channel is offline
        twitchEmbedElement.innerHTML = `
        `;
      }
    })
    .catch(error => {
      console.error('Error checking Twitch live status:', error);
    });
}

// Check live status when the page loads
document.addEventListener('DOMContentLoaded', checkLiveStatus);

// Check live status every 5 minutes
setInterval(checkLiveStatus, 5 * 60 * 1000);
