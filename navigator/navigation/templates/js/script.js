function navClick(name) {
    alert(`Navigated to ${name}`);
  }
  
  function likePost(button) {
    button.textContent = "Liked!";
    button.style.backgroundColor = "green";
  }
  
  function trendClick(tag) {
    alert(`Opening trend: ${tag}`);
  }
  

  let qrScanner;

  function openQRScanner() {
    console.log("Opening QR Scanner..."); // Debugging log
    document.getElementById("qrModal").style.display = "flex";
  
    qrScanner = new Html5Qrcode("qr-reader");
  
    qrScanner.start(
      { facingMode: "environment" },
      {
        fps: 10,
        qrbox: 250,
      },
      (decodedText) => {
        try {
          qrData = JSON.parse(decodedText); // Update the global qrData variable
          console.log("QR Code Data:", qrData); // Debugging log
  
          // Update the UI to show the destination section
          document.getElementById("destination-section").style.display = "block";
  
          // Populate the destination dropdown with the scanned coordinates
          const destinationSelect = document.getElementById("destination-select");
          destinationSelect.innerHTML = ""; // Clear existing options
          const option = document.createElement("option");
          option.value = JSON.stringify({
            latitude: qrData.lat,
            longitude: qrData.lng,
          });
          option.textContent = `${qrData.label} (Lat: ${qrData.lat}, Lng: ${qrData.lng})`;
          destinationSelect.appendChild(option);
        } catch (error) {
          console.error("Error parsing QR code data:", error);
          alert("Invalid QR code format.");
        } finally {
          closeQRScanner();
        }
      },
      (error) => {
        console.error("QR Code Scanning Error:", error); // Debugging log
      }
    ).catch((err) => {
      console.error("Error Starting QR Scanner:", err); // Debugging log
    });
  }
  
  function closeQRScanner() {
    document.getElementById("qrModal").style.display = "none";
  }

  function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");
    sidebar.classList.toggle("open");

    // Add or remove overlay for dismissing the sidebar
    if (sidebar.classList.contains("open")) {
      document.body.insertAdjacentHTML(
        "beforeend",
        '<div id="sidebarOverlay" class="sidebar-overlay" onclick="dismissSidebar()"></div>'
      );
    } else {
      dismissSidebar();
    }
  }

  function dismissSidebar() {
    const sidebar = document.getElementById("sidebar");
    sidebar.classList.remove("open");

    const overlay = document.getElementById("sidebarOverlay");
    if (overlay) {
      overlay.remove();
    }
  }

// Detect unsupported browsers or embedded browsers
function isUnsupportedBrowser() {
  const userAgent = navigator.userAgent || navigator.vendor || window.opera;

  // Check for embedded browsers (e.g., apps like Instagram, Facebook, etc.)
  const isEmbedded = /FBAN|FBAV|Instagram|Line|Twitter|Snapchat|WebView/i.test(userAgent);

  // Check if the browser is Chrome
  const isChrome = /Chrome/i.test(userAgent) && !/Edg/i.test(userAgent) && !/OPR/i.test(userAgent);

  // Return true if it's an embedded browser or not Chrome
  return isEmbedded || !isChrome;
}

// Redirect or show a message
if (isUnsupportedBrowser()) {
  const currentUrl = window.location.href;

  document.body.innerHTML = `
    <div style="text-align: center; margin-top: 50px; font-family: 'Segoe UI', sans-serif; color: #fff; background-color: #000; height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center;">
      <h1>Open in Chrome</h1>
      <p>This app works best in Google Chrome and requires access to your camera, which may not be supported in this browser or app.</p>
      <p>Please copy the link below and open it in Google Chrome for full functionality:</p>
      <input type="text" value="${currentUrl}" readonly style="width: 80%; padding: 10px; margin: 10px 0; text-align: center; font-size: 16px; border: none; border-radius: 5px; background-color: #333; color: #fff;">
      <button onclick="copyToClipboard('${currentUrl}')" style="padding: 10px 20px; font-size: 16px; border: none; border-radius: 5px; background-color: #007bff; color: #fff; cursor: pointer;">Copy Link</button>
    </div>
  `;
}

// Function to copy the URL to the clipboard
function copyToClipboard(url) {
  navigator.clipboard.writeText(url).then(() => {
    alert('Link copied to clipboard! Please paste it in Google Chrome.');
  });
}
