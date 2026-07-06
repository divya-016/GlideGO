// ============================================================
//  GLIDE GO — ESP32 Final Code
//  WiFi control + Smooth acceleration + SR04 obstacle detection
//
//  PIN CONNECTIONS:
//  Motor L  → RPWM = GPIO 25,  LPWM = GPIO 26
//  Motor R  → RPWM = GPIO 14,  LPWM = GPIO 27
//  BTS7960 R_EN + L_EN → GPIO 15
//  HC-SR04  → Trig = GPIO 4,   Echo = GPIO 2
//
//  UPLOAD via USB (COM3)
//  After upload: disconnect USB, power via battery
// ============================================================

#include <WiFi.h>

// --- HOTSPOT CREDENTIALS ---
const char* ssid     = "divya's A14";
const char* password = "lucky007";

// --- WiFi Server ---
WiFiServer server(8888);
WiFiClient client;

// --- Motor L pins ---
#define ML_RPWM 25
#define ML_LPWM 26

// --- Motor R pins ---
#define MR_RPWM 14
#define MR_LPWM 27

// --- Enable pin (both BTS7960) ---
#define EN_PIN 15

// --- HC-SR04 pins ---
#define TRIG_PIN 4
#define ECHO_PIN 2

// ============================================================
//  TUNABLE SETTINGS
// ============================================================
#define MAX_SPEED        160   // top speed 0-255 (160 = medium walking pace)
#define MIN_SPEED         50   // starting speed when ramping up
#define ACCEL_STEP         3   // speed increase per ramp step (smaller = smoother)
#define ACCEL_DELAY_MS    30   // ms between ramp steps (3-4 sec to full speed)
#define DECEL_STEP         4   // speed decrease per ramp step
#define DECEL_DELAY_MS    25   // ms between decel steps
#define CMD_HOLD_MS     2000   // 2 seconds between command switches
#define SR04_INTERVAL_MS 100   // obstacle check every 100ms
#define OBSTACLE_DIST_CM  25   // stop if object closer than 25cm
#define SAFE_DIST_CM      30   // resume only when object beyond 30cm

// ============================================================
//  STATE VARIABLES
// ============================================================
int           currentSpeed    = 0;
char          currentCmd      = 'S';
char          pendingCmd      = 'S';
bool          obstacleBlocked = false;
unsigned long lastCmdTime     = 0;
unsigned long lastSR04Time    = 0;
float         lastDistance    = 999.0;

// ============================================================
//  SETUP
// ============================================================
void setup() {
  Serial.begin(115200);
  Serial.println("\nGLIDE GO starting...");

  // Motor pins
  pinMode(ML_RPWM, OUTPUT);
  pinMode(ML_LPWM, OUTPUT);
  pinMode(MR_RPWM, OUTPUT);
  pinMode(MR_LPWM, OUTPUT);

  // Enable both BTS7960 drivers
  pinMode(EN_PIN, OUTPUT);
  digitalWrite(EN_PIN, HIGH);

  // SR04
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  hardStop();

  // Connect to hotspot
  Serial.print("Connecting to: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    attempts++;
    if (attempts > 40) {
      Serial.println("\nWiFi failed! Check hotspot is ON and restart.");
      return;
    }
  }

  Serial.println("\nWiFi connected!");
  Serial.print("ESP32 IP Address: ");
  Serial.println(WiFi.localIP());   // COPY THIS IP INTO PYTHON FILE
  Serial.println("Waiting for Python on port 8888...");
  server.begin();
}

// ============================================================
//  MAIN LOOP
// ============================================================
void loop() {

  // Accept new Python connection
  if (!client || !client.connected()) {
    client = server.accept();
    if (client) {
      Serial.println("Python connected!");
      client.println("GLIDE_GO_READY");
      hardStop();
      obstacleBlocked = false;
      currentCmd = 'S';
      pendingCmd = 'S';
    }
  }

  if (client && client.connected()) {

    unsigned long now = millis();

    // ── SR04 OBSTACLE CHECK every 100ms ──
    if (now - lastSR04Time >= SR04_INTERVAL_MS) {
      lastSR04Time = now;
      lastDistance = getDistance();

      if (!obstacleBlocked && lastDistance > 0 && lastDistance < OBSTACLE_DIST_CM) {
        obstacleBlocked = true;
        gradualStop();
        Serial.print("OBSTACLE at ");
        Serial.print(lastDistance);
        Serial.println("cm — stopped");
        client.println("OBSTACLE:" + String(lastDistance, 1) + "cm");
      }
      else if (obstacleBlocked && lastDistance >= SAFE_DIST_CM) {
        obstacleBlocked = false;
        Serial.println("Path clear — resuming");
        client.println("CLEAR:Path clear");
      }

      client.println("DIST:" + String(lastDistance, 1));
    }

    // ── READ GESTURE COMMAND FROM PYTHON ──
    if (client.available()) {
      char incoming = client.read();
      if (incoming != currentCmd) {
        pendingCmd = incoming;
      }
    }

    // ── APPLY PENDING COMMAND AFTER 2 SECOND DELAY ──
    if (pendingCmd != currentCmd && (millis() - lastCmdTime) >= CMD_HOLD_MS) {
      Serial.print("Applying CMD: ");
      Serial.println(pendingCmd);
      if (currentSpeed > 0) gradualStop();
      currentCmd  = pendingCmd;
      lastCmdTime = millis();
    }

    // ── EXECUTE COMMAND (only if no obstacle) ──
    if (!obstacleBlocked) {
      switch (currentCmd) {
        case 'F': rampUp(true,  true);  break;   // both forward
        case 'B': rampUp(false, false); break;   // both backward
        case 'L': rampUp(false, true);  break;   // turn left
        case 'R': rampUp(true,  false); break;   // turn right
        case 'S':
          if (currentSpeed > 0) gradualStop();
          break;
        default:
          hardStop();
          currentCmd = 'S';
          break;
      }
    }

  } else {
    hardStop();
    currentCmd      = 'S';
    pendingCmd      = 'S';
    obstacleBlocked = false;
  }
}

// ============================================================
//  RAMP UP — gradual acceleration
// ============================================================
void rampUp(bool leftFwd, bool rightFwd) {
  if (currentSpeed < MAX_SPEED) {
    if (currentSpeed == 0) currentSpeed = MIN_SPEED;
    else currentSpeed = min(currentSpeed + ACCEL_STEP, MAX_SPEED);
    delay(ACCEL_DELAY_MS);
  }
  setMotors(leftFwd, rightFwd, currentSpeed);
}

// ============================================================
//  GRADUAL STOP — smooth deceleration
// ============================================================
void gradualStop() {
  while (currentSpeed > 0) {
    currentSpeed = max(currentSpeed - DECEL_STEP, 0);
    switch (currentCmd) {
      case 'F': setMotors(true,  true,  currentSpeed); break;
      case 'B': setMotors(false, false, currentSpeed); break;
      case 'L': setMotors(false, true,  currentSpeed); break;
      case 'R': setMotors(true,  false, currentSpeed); break;
      default:  setMotors(true,  true,  currentSpeed); break;
    }
    delay(DECEL_DELAY_MS);
  }
  hardStop();
}

// ============================================================
//  HARD STOP — instant emergency stop
// ============================================================
void hardStop() {
  currentSpeed = 0;
  analogWrite(ML_RPWM, 0);
  analogWrite(ML_LPWM, 0);
  analogWrite(MR_RPWM, 0);
  analogWrite(MR_LPWM, 0);
}

// ============================================================
//  SET MOTORS
// ============================================================
void setMotors(bool leftFwd, bool rightFwd, int spd) {
  if (leftFwd) {
    analogWrite(ML_RPWM, spd);
    analogWrite(ML_LPWM, 0);
  } else {
    analogWrite(ML_RPWM, 0);
    analogWrite(ML_LPWM, spd);
  }
  if (rightFwd) {
    analogWrite(MR_RPWM, spd);
    analogWrite(MR_LPWM, 0);
  } else {
    analogWrite(MR_RPWM, 0);
    analogWrite(MR_LPWM, spd);
  }
}

// ============================================================
//  HC-SR04 DISTANCE
// ============================================================
float getDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  if (duration == 0) return 999.0;
  return (duration * 0.0343) / 2.0;
}
