async function checkLiveStatus() {
  const twitchEmbedElement = document.getElementById('twitch-embed');
  
  if (!twitchEmbedElement) {
    console.error('Twitch embed element not found');
    return;
  }

  console.log('Checking live status...');
  try {
    const response = await fetch('https://twitch-token-renewer.dfm-titus.workers.dev/check-status');
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('Response from worker:', data);

    if (data.isLive) {
      console.log('Channel is live, updating embed');
      twitchEmbedElement.innerHTML = `
        <iframe
          src="https://player.twitch.tv/?channel=${data.channelName}&parent=${window.location.hostname}"
          height="480"
          width="100%"
          allowfullscreen>
        </iframe>
      `;
    } else {
      console.log('Channel is offline, clearing embed');
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
