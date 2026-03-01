# 🧪 SeeWhozThere Testing Guide

This guide provides a comprehensive checklist for testing the SeeWhozThere system to ensure all features are working correctly.

## 📋 Prerequisites

- SeeWhozThere is installed and running (either via Docker or systemd).
- At least one camera is configured and active.
- You have access to the web dashboard.

## 🎯 Testing Checklist

### **1. Core System**

| Test Case | Steps | Expected Result | Status |
|---|---|---|---|
| **Service Status** | 1. Run `docker-compose ps` or `sudo systemctl status seewhozthere seewhozthere-web`. | Both services should be `running` or `active`. | ☐ |
| **Web Dashboard** | 1. Open `http://YOUR_PI_IP:7222/dashboard` in a browser. | The dashboard loads without errors. | ☐ |
| **System Status Indicator** | 1. Look at the top-right of the dashboard. | The status indicator should be green and say "Active". | ☐ |

### **2. Face Detection & Recognition**

| Test Case | Steps | Expected Result | Status |
|---|---|---|---|
| **Unknown Face Detection** | 1. Walk in front of the camera. | An "Unknown" visitor card appears on the dashboard within 10-20 seconds. | ☐ |
| **Add New Person** | 1. Click "Add Person".<br>2. Enter a name.<br>3. Upload a clear photo.<br>4. Click "Add Person". | A success notification appears. The person is added to the "Manage People" list. | ☐ |
| **Known Face Recognition** | 1. After adding a person, walk in front of the camera again. | A new card appears with the correct name. The "Known vs Unknown" chart updates. | ☐ |
| **Multiple Detections** | 1. Have multiple people in the camera view. | Multiple visitor cards should appear. | ☐ |

### **3. Dashboard Functionality**

| Test Case | Steps | Expected Result | Status |
|---|---|---|---|
| **Stats Cards** | 1. Observe the 4 cards at the top. | The numbers should be non-zero and update as new events occur. | ☐ |
| **Hourly Activity Chart** | 1. Look at the hourly bar chart. | The bars should reflect the number of known/unknown detections per hour. | ☐ |
| **Known vs Unknown Chart** | 1. Look at the pie chart. | The chart should show the ratio of known to unknown visitors. | ☐ |
| **Weekly Trend Chart** | 1. Observe the line chart. | It should show a trend line for the last 7 days. | ☐ |
| **Camera Activity Chart** | 1. Look at the camera bar chart. | It should show the number of detections per camera. | ☐ |
| **Top Visitors List** | 1. Observe the list on the right. | It should show the most frequently seen known visitors. | ☐ |
| **Peak Hours Heatmap** | 1. Look at the heatmap. | It should show colored squares indicating busy times. | ☐ |
| **Visitor Grid** | 1. Scroll down to the visitor grid. | It should show cards for all visitors seen today. | ☐ |
| **Delete Sighting** | 1. Click the trash icon on a visitor card. | The card is removed from the dashboard. | ☐ |

### **4. User Management**

| Test Case | Steps | Expected Result | Status |
|---|---|---|---|
| **Manage People Modal** | 1. Click "Manage People" in the navigation. | A modal appears with a list of all known people. | ☐ |
| **Delete Person** | 1. In the "Manage People" modal, click the trash icon next to a person. | The person is removed from the list. Future detections of this person will be "Unknown". | ☐ |

### **5. System & Configuration**

| Test Case | Steps | Expected Result | Status |
|---|---|---|---|
| **Data Persistence** | 1. Restart the container (`docker-compose restart`) or the Pi.<br>2. Check the dashboard. | All data (visitors, sightings, etc.) should still be present. | ☐ |
| **Log Files** | 1. Check the `data/` directory or run `docker-compose logs`. | Log files should exist and contain recent entries. | ☐ |
| **Configuration Update** | 1. Stop the system.<br>2. Edit `config.ini` to add a new camera.<br>3. Start the system. | The new camera should be active and appear in the dashboard. | ☐ |

## 🐛 Troubleshooting

### **No Detections**
- **Check Camera URL:** Verify the RTSP URL in `config.ini` is correct.
- **Check Logs:** Run `docker-compose logs -f` to look for camera connection errors.
- **Check Hailo Device:** Ensure the AI HAT+ is properly connected and the `/dev/hailo0` device exists.

### **Dashboard Not Loading**
- **Check Service:** Make sure the `seewhozthere` container is running (`docker-compose ps`).
- **Check Port:** Ensure port 7222 is not blocked by a firewall.
- **Check Build:** If you built manually, ensure the React app was built and copied correctly.

### **Incorrect Recognition**
- **Use Clear Photos:** Ensure the photos you upload for training are clear and well-lit.
- **Adjust Threshold:** You can adjust `recognition_threshold` in `app/face_recognition_engine.py` (lower = stricter).

## 📊 Performance Testing

### **CPU & Memory Usage**
- Run `docker stats seewhozthere` to monitor resource usage.
- **Expected:** CPU usage will be high (40-80%) during active detection. This is normal.
- **Expected:** Memory usage should be stable (500MB - 1.5GB).

### **Detection Speed**
- Detections should appear on the dashboard within 10-20 seconds of the event.
- The system processes frames every 1-2 seconds (configurable).

## 📝 Notes

- **Initial Startup:** The first run may take a few minutes to load AI models.
- **Data Reset:** To start fresh, stop the container, delete the `data/` directory, and restart.

---

**Happy Testing! 🧪**
