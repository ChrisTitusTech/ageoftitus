const channelName = 'TitusTechGaming';
const clientId = 'au9081y3ft41wtb1p4im5502qy5emu';

// Move this inside the function to ensure the element exists when the script runs
// const twitchEmbedElement = document.getElementById('twitch-embed');

async function checkLiveStatus() {
  const twitchEmbedElement = document.getElementById('twitch-embed');
  
  if (!twitchEmbedElement) {
    console.error('Twitch embed element not found');
    return;
  }

  try {
    const response = await fetch('https://twitch-token-renewer.dfm-titus.workers.dev', {
      headers: {
        'Client-ID': clientId
      }
    });
    const data = await response.json();

    if (data.isLive) {
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
      twitchEmbedElement.innerHTML = '';
    }
  } catch (error) {
    console.error('Error checking Twitch live status:', error);
  }
}

// Check live status when the page loads
document.addEventListener('DOMContentLoaded', checkLiveStatus);

// Check live status every 5 minutes
setInterval(checkLiveStatus, 5 * 60 * 1000);
