import cv2
import requests
import numpy as np
import time
from roboflow import Roboflow

# ==========================================
# 1. KONFIGURASI
# ==========================================
# Pastikan IP ini SAMA PERSIS dengan yang di Browser
URL_STREAM = "http://10.158.108.122/stream" 

BLYNK_AUTH_TOKEN = "ILjW7P0cRKDoSy3VmS0qLinNUrz1XWgR"
BLYNK_VPIN = "V3"

RF_API_KEY = "PwueEaA3ltu56lz0OMjE"
RF_PROJECT_ID = "sampah-jhryl"
RF_VERSION = 2

# ==========================================
# 2. SETUP AI
# ==========================================
print("1. Menghubungkan ke Roboflow...")
try:
    rf = Roboflow(api_key=RF_API_KEY)
    project = rf.workspace().project(RF_PROJECT_ID)
    model = project.version(RF_VERSION).model
    print("✅ Model AI Siap!")
except:
    print("⚠️ Gagal load Roboflow. Program akan jalan mode 'Cek Kamera' saja.")
    model = None

def kirim_blynk(pesan):
    try:
        url = f"https://blynk.cloud/external/api/update?token={BLYNK_AUTH_TOKEN}&{BLYNK_VPIN}={pesan}"
        requests.get(url, timeout=0.1)
    except:
        pass

# ==========================================
# 3. LOOP UTAMA (METODE PARSING MANUAL)
# ==========================================
print(f"2. Membuka stream dari: {URL_STREAM}")
print("   (Jendela mungkin hitam jika ruangan gelap. SOROT PAKAI SENTER!)")

try:
    # Kita download stream secara manual (lebih stabil)
    stream = requests.get(URL_STREAM, stream=True, timeout=5)
    
    if stream.status_code == 200:
        bytes_data = b''
        nama_terakhir = ""
        
        # Baca data sedikit demi sedikit
        for chunk in stream.iter_content(chunk_size=1024):
            bytes_data += chunk
            
            # Cari tanda awal (FF D8) gambar JPG
            a = bytes_data.find(b'\xff\xd8')
            
            if a != -1:
                # Cari tanda akhir (FF D9) SETELAH tanda awal
                b = bytes_data.find(b'\xff\xd9', a)
                
                if b != -1:
                    # Kita dapat 1 foto utuh!
                    jpg = bytes_data[a:b+2]
                    bytes_data = bytes_data[b+2:] # Simpan sisa untuk frame berikutnya
                    
                    try:
                        # Decode gambar
                        frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                        
                        if frame is not None:
                            # ---------------------------
                            # DETEKSI AI DISINI
                            # ---------------------------
                            if model:
                                try:
                                    # Confidence diturunkan ke 10 biar sensitif utk testing
                                    prediction = model.predict(frame, confidence=10, overlap=30).json()
                                    items = prediction['predictions']
                                    
                                    if len(items) > 0:
                                        objek = items[0]
                                        nama = objek['class'].upper()
                                        
                                        # Gambar Kotak
                                        x, y, w, h = int(objek['x']), int(objek['y']), int(objek['width']), int(objek['height'])
                                        x1, y1 = int(x - w/2), int(y - h/2)
                                        x2, y2 = int(x + w/2), int(y + h/2)
                                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                        cv2.putText(frame, nama, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                        
                                        if nama != nama_terakhir:
                                            kirim_blynk(nama)
                                            print(f"Deteksi: {nama}")
                                            nama_terakhir = nama
                                    else:
                                        if nama_terakhir != "MENUNGGU...":
                                            kirim_blynk("MENUNGGU...")
                                            nama_terakhir = "MENUNGGU..."
                                except:
                                    pass

                            cv2.imshow("MONITORING AI (ANTI-LAG)", frame)
                            
                            # Tekan 'q' untuk keluar
                            if cv2.waitKey(1) == ord('q'):
                                break
                    except:
                        # Jika gambar rusak, abaikan (jangan crash)
                        pass
    else:
        print("❌ Gagal konek ke Stream.")

except Exception as e:
    print(f"❌ Error Koneksi: {e}")

cv2.destroyAllWindows()