package main

import (
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"
	"unsafe"

	"github.com/jchv/go-webview2"
	"golang.org/x/sys/windows"
)

var (
	user32                    = syscall.NewLazyDLL("user32.dll")
	procMessageBoxW           = user32.NewProc("MessageBoxW")
	dwmapi                    = syscall.NewLazyDLL("dwmapi.dll")
	procDwmSetWindowAttribute = dwmapi.NewProc("DwmSetWindowAttribute")
	kernel32                  = syscall.NewLazyDLL("kernel32.dll")
	procGetModuleHandleW      = kernel32.NewProc("GetModuleHandleW")
	procLoadImageW            = user32.NewProc("LoadImageW")
	procSendMessageW          = user32.NewProc("SendMessageW")
	procGetWindowPlacement    = user32.NewProc("GetWindowPlacement")
	procSetWindowPlacement    = user32.NewProc("SetWindowPlacement")
	procGetWindowLongW        = user32.NewProc("GetWindowLongW")
	procSetWindowLongW        = user32.NewProc("SetWindowLongW")
	procSetWindowPos          = user32.NewProc("SetWindowPos")
	procMonitorFromWindow     = user32.NewProc("MonitorFromWindow")
	procGetMonitorInfoW       = user32.NewProc("GetMonitorInfoW")
)

const (
	MB_OK            = 0x00000000
	MB_ICONERROR     = 0x00000010
	MB_ICONWARNING   = 0x00000030
	CREATE_NO_WINDOW = 0x08000000
	// DWMWA_USE_IMMERSIVE_DARK_MODE: 20 untuk Win10 1903+,
	// 19 untuk build lama. Border/titlebar ikut tema sistem.
	DWMWA_USE_IMMERSIVE_DARK_MODE_NEW = 20
	DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19

	// Win32 constants untuk fullscreen monitor
	WS_OVERLAPPEDWINDOW      = 0x00CF0000
	WS_POPUP                 = 0x80000000
	WS_VISIBLE               = 0x10000000
	SWP_NOSIZE               = 0x0001
	SWP_NOMOVE               = 0x0002
	SWP_NOZORDER             = 0x0004
	SWP_NOOWNERZORDER        = 0x0200
	SWP_FRAMECHANGED         = 0x0020
	SWP_SHOWWINDOW           = 0x0040
	MONITOR_DEFAULTTONEAREST = 0x00000002
)

type RECT struct {
	Left   int32
	Top    int32
	Right  int32
	Bottom int32
}

type POINT struct {
	X int32
	Y int32
}

type WINDOWPLACEMENT struct {
	Length           uint32
	Flags            uint32
	ShowCmd          uint32
	PtMinPosition    POINT
	PtMaxPosition    POINT
	RcNormalPosition RECT
}

type MONITORINFO struct {
	CbSize    uint32
	RcMonitor RECT
	RcWork    RECT
	DwFlags   uint32
}

var (
	isNativeFullscreen bool
	prevPlacement      WINDOWPLACEMENT
	prevStyle          uint32
)

func setNativeFullscreen(hwnd uintptr, fullscreen bool) {
	if hwnd == 0 {
		return
	}
	if fullscreen == isNativeFullscreen {
		return
	}

	var idx int32 = -16 // GWL_STYLE
	if fullscreen {
		prevPlacement.Length = uint32(unsafe.Sizeof(prevPlacement))
		ret, _, _ := procGetWindowPlacement.Call(hwnd, uintptr(unsafe.Pointer(&prevPlacement)))
		if ret == 0 {
			return
		}

		styleRet, _, _ := procGetWindowLongW.Call(hwnd, uintptr(idx))
		prevStyle = uint32(styleRet)

		hMon, _, _ := procMonitorFromWindow.Call(hwnd, MONITOR_DEFAULTTONEAREST)
		if hMon == 0 {
			return
		}

		var mi MONITORINFO
		mi.CbSize = uint32(unsafe.Sizeof(mi))
		ret, _, _ = procGetMonitorInfoW.Call(hMon, uintptr(unsafe.Pointer(&mi)))
		if ret == 0 {
			return
		}

		newStyle := (prevStyle &^ WS_OVERLAPPEDWINDOW) | WS_POPUP | WS_VISIBLE
		procSetWindowLongW.Call(hwnd, uintptr(idx), uintptr(newStyle))

		width := mi.RcMonitor.Right - mi.RcMonitor.Left
		height := mi.RcMonitor.Bottom - mi.RcMonitor.Top

		procSetWindowPos.Call(
			hwnd,
			0, // HWND_TOP
			uintptr(mi.RcMonitor.Left),
			uintptr(mi.RcMonitor.Top),
			uintptr(width),
			uintptr(height),
			SWP_NOOWNERZORDER|SWP_FRAMECHANGED|SWP_SHOWWINDOW,
		)
		isNativeFullscreen = true
	} else {
		if prevStyle != 0 {
			procSetWindowLongW.Call(hwnd, uintptr(idx), uintptr(prevStyle))
		}
		if prevPlacement.Length != 0 {
			procSetWindowPlacement.Call(hwnd, uintptr(unsafe.Pointer(&prevPlacement)))
		}
		procSetWindowPos.Call(
			hwnd,
			0,
			0, 0, 0, 0,
			SWP_NOMOVE|SWP_NOSIZE|SWP_NOZORDER|SWP_NOOWNERZORDER|SWP_FRAMECHANGED,
		)
		isNativeFullscreen = false
	}
}

func showMessage(title, text string, flags uint) {
	t, _ := syscall.UTF16PtrFromString(title)
	m, _ := syscall.UTF16PtrFromString(text)
	procMessageBoxW.Call(0, uintptr(unsafe.Pointer(m)), uintptr(unsafe.Pointer(t)), uintptr(flags))
}

func isServerRunning(url string) bool {
	client := http.Client{
		Timeout: 1 * time.Second,
	}
	resp, err := client.Get(url)
	if err == nil && resp.StatusCode == 200 {
		resp.Body.Close()
		return true
	}
	return false
}

func isPortListening(port int) bool {
	conn, err := net.DialTimeout("tcp", fmt.Sprintf("127.0.0.1:%d", port), 200*time.Millisecond)
	if err == nil {
		conn.Close()
		return true
	}
	return false
}

func terminateProcessByPID(pid int) {
	h, err := windows.OpenProcess(windows.PROCESS_TERMINATE, false, uint32(pid))
	if err == nil {
		_ = windows.TerminateProcess(h, 1)
		_ = windows.CloseHandle(h)
	}
}

func freeServerPort(appDir string, port int) {
	// 1. Coba kirim shutdown graceful via HTTP ke backend jika masih merespons
	shutdownURL := fmt.Sprintf("http://127.0.0.1:%d/api/shutdown", port)
	client := http.Client{Timeout: 600 * time.Millisecond}
	req, err := http.NewRequest("POST", shutdownURL, nil)
	if err == nil {
		if resp, err := client.Do(req); err == nil {
			resp.Body.Close()
		}
	}

	// 2. Cek apakah ada file PID tersimpan dari sesi sebelumnya untuk di-terminate
	pidFile := filepath.Join(appDir, "cache", "server.pid")
	if data, err := os.ReadFile(pidFile); err == nil {
		if pid, err := strconv.Atoi(strings.TrimSpace(string(data))); err == nil && pid > 0 {
			terminateProcessByPID(pid)
		}
		_ = os.Remove(pidFile)
	}

	// 3. Tunggu hingga port benar-benar bebas (maksimal 1 detik)
	for i := 0; i < 10; i++ {
		if !isPortListening(port) {
			break
		}
		time.Sleep(100 * time.Millisecond)
	}
}

func getLastLogLines(logPath string, maxLines int) string {
	b, err := os.ReadFile(logPath)
	if err != nil {
		return ""
	}
	lines := strings.Split(string(b), "\n")
	if len(lines) > maxLines {
		lines = lines[len(lines)-maxLines:]
	}
	return strings.Join(lines, "\n")
}

func acquireSingleInstance() (release func(), ok bool) {
	name, _ := windows.UTF16PtrFromString(`Local\TatapSingleInstance_v2`)
	h, err := windows.CreateMutex(nil, false, name)
	if err != nil {
		return func() {}, false
	}
	if windows.GetLastError() == windows.ERROR_ALREADY_EXISTS {
		windows.CloseHandle(h)
		return func() {}, false
	}
	return func() { windows.CloseHandle(h) }, true
}

func isSystemDarkMode() bool {
	// HKCU\...\Themes\Personalize\AppsUseLightTheme: 0 = dark, 1 = light.
	sub, _ := windows.UTF16PtrFromString(`Software\Microsoft\Windows\CurrentVersion\Themes\Personalize`)
	name, _ := windows.UTF16PtrFromString(`AppsUseLightTheme`)
	var k windows.Handle
	if err := windows.RegOpenKeyEx(windows.HKEY_CURRENT_USER, sub, 0, windows.KEY_READ, &k); err != nil {
		return true
	}
	defer windows.RegCloseKey(k)
	var typ, val uint32
	var n uint32 = 4
	if err := windows.RegQueryValueEx(k, name, nil, &typ, (*byte)(unsafe.Pointer(&val)), &n); err != nil {
		return true
	}
	return val == 0
}

func setDarkMode(hwnd uintptr, dark bool) {
	var v int32
	if dark {
		v = 1
	}
	pv := uintptr(unsafe.Pointer(&v))
	for _, attr := range []uintptr{DWMWA_USE_IMMERSIVE_DARK_MODE_NEW, DWMWA_USE_IMMERSIVE_DARK_MODE_OLD} {
		r, _, _ := procDwmSetWindowAttribute.Call(hwnd, attr, pv, 4)
		if r == 0 {
			return
		}
	}
}

func setWindowIcons(hwnd uintptr) {
	// Load icon dari RT_GROUP_ICON id 1 (lihat launcher/winres/winres.json).
	// Kirim WM_SETICON ICON_SMALL/BIG agar Windows pakai untuk taskbar/alt-tab.
	hInstance, _, _ := procGetModuleHandleW.Call()
	hIcon, _, _ := procLoadImageW.Call(
		hInstance, 1 /*resource id*/, 1 /*IMAGE_ICON*/, 0, 0,
		0x00000040 /*LR_DEFAULTSIZE=0x40*/|0x00008000 /*LR_SHARED=0x8000*/)
	if hIcon == 0 {
		return
	}
	// ICON_SMALL=0, ICON_BIG=1
	procSendMessageW.Call(hwnd, 0x00000080 /*WM_SETICON*/, 0, hIcon)
	procSendMessageW.Call(hwnd, 0x00000080 /*WM_SETICON*/, 1, hIcon)
}

func runWebView(appURL, dataPath string) {
	w := webview2.NewWithOptions(webview2.WebViewOptions{
		Debug:     false,
		AutoFocus: true,
		DataPath:  dataPath,
		WindowOptions: webview2.WindowOptions{
			Title:  "Tatap - Nonton Santai di Lokal",
			Width:  1280,
			Height: 800,
			Center: true,
			// IconId 1 cocok dengan RT_GROUP_ICON "#1" di launcher/winres/winres.json.
			// Library panggil LoadImageW(hinstance, MAKEINTRESOURCE(1), ...)
			// yang otomatis load dari resource RT_GROUP_ICON id 1 (lihat PNG).
			IconId: 1,
		},
	})
	if w == nil {
		showMessage("Tatap - Kesalahan",
			"WebView2 runtime tidak ditemukan.\n\nInstall Microsoft Edge WebView2 Runtime dari:\nhttps://developer.microsoft.com/microsoft-edge/webview2/",
			MB_OK|MB_ICONERROR)
		return
	}
	defer w.Destroy()
	hwnd := uintptr(w.Window())
	setDarkMode(hwnd, isSystemDarkMode())
	// Backup: pastikan icon tampil di taskbar/alt-tab dengan WM_SETICON
	// (beberapa Windows theme abaikan HIconSm dari WNDCLASSEX).
	setWindowIcons(hwnd)

	// Bridge JS tatap_set_fullscreen untuk monitor fullscreen tanpa border
	_ = w.Bind("tatap_set_fullscreen", func(fullscreen bool) error {
		setNativeFullscreen(hwnd, fullscreen)
		return nil
	})

	w.Navigate(appURL)
	w.Run()
}

func main() {
	log.SetOutput(os.Stderr)

	release, single := acquireSingleInstance()
	if !single {
		return
	}
	defer release()

	exePath, err := os.Executable()
	if err != nil {
		exePath, _ = filepath.Abs(os.Args[0])
	}
	appDir := filepath.Dir(exePath)
	appURL := "http://127.0.0.1:8767"
	pingURL := appURL + "/api/ping"

	var pyCmd *exec.Cmd

	// 1. Cek apakah server sudah aktif dan sehat
	if !isServerRunning(pingURL) {
		// 2. Bersihkan instance backend lama di port 8767 secara graceful
		freeServerPort(appDir, 8767)

		// 3. Tentukan path python.exe dan backend/main.py
		pythonExe := filepath.Join(appDir, "runtime", "python.exe")
		if _, err := os.Stat(pythonExe); os.IsNotExist(err) {
			p, errLook := exec.LookPath("python.exe")
			if errLook != nil {
				p, errLook = exec.LookPath("python")
			}
			if errLook != nil {
				showMessage("Tatap - Kesalahan", "Runtime Python tidak ditemukan di folder 'runtime\\python.exe' atau di sistem.", MB_OK|MB_ICONERROR)
				return
			}
			pythonExe = p
		}

		backendMain := filepath.Join(appDir, "backend", "main.py")
		if _, err := os.Stat(backendMain); os.IsNotExist(err) {
			showMessage("Tatap - Kesalahan", fmt.Sprintf("File backend tidak ditemukan:\n%s", backendMain), MB_OK|MB_ICONERROR)
			return
		}

		// Siapkan folder cache untuk log
		cacheDir := filepath.Join(appDir, "cache")
		_ = os.MkdirAll(cacheDir, 0755)
		logPath := filepath.Join(cacheDir, "server.log")
		logFile, err := os.OpenFile(logPath, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0644)

		// 4. Jalankan backend Python
		pyCmd = exec.Command(pythonExe, backendMain)
		pyCmd.Dir = appDir
		pyCmd.SysProcAttr = &syscall.SysProcAttr{
			HideWindow:    true,
			CreationFlags: CREATE_NO_WINDOW,
		}
		if err == nil {
			pyCmd.Stdout = logFile
			pyCmd.Stderr = logFile
			defer logFile.Close()
		}

		if err := pyCmd.Start(); err != nil {
			showMessage("Tatap - Gagal Start", fmt.Sprintf("Gagal menyalakan proses backend: %v", err), MB_OK|MB_ICONERROR)
			return
		}

		// Simpan PID proses backend untuk recovery jika crash/force exit
		if pyCmd.Process != nil {
			pidFile := filepath.Join(cacheDir, "server.pid")
			_ = os.WriteFile(pidFile, []byte(strconv.Itoa(pyCmd.Process.Pid)), 0644)
		}

		// 5. Polling hingga /api/ping merespons (maksimal 15 detik)
		ready := false
		for i := 0; i < 75; i++ {
			time.Sleep(200 * time.Millisecond)
			if isServerRunning(pingURL) {
				ready = true
				break
			}

			if pyCmd.Process != nil {
				var status uint32
				handle := syscall.Handle(pyCmd.Process.Pid)
				if syscall.GetExitCodeProcess(handle, &status) == nil && status != 259 { // 259 = STILL_ACTIVE
					break
				}
			}
		}

		if !ready {
			if pyCmd.Process != nil {
				_ = pyCmd.Process.Kill()
				pidFile := filepath.Join(cacheDir, "server.pid")
				_ = os.Remove(pidFile)
			}
			logSnippet := getLastLogLines(logPath, 10)
			msg := "Server backend tidak dapat berjalan atau gagal merespons dalam 15 detik."
			if strings.TrimSpace(logSnippet) != "" {
				msg += "\n\nLog Kesalahan Terakhir:\n" + logSnippet
			}
			showMessage("Tatap - Gagal Memulai", msg, MB_OK|MB_ICONERROR)
			return
		}
	}

	// 6. Window close -> kill background processes yang kita spawn
	if pyCmd != nil && pyCmd.Process != nil {
		defer func() {
			_ = pyCmd.Process.Kill()
			pidFile := filepath.Join(appDir, "cache", "server.pid")
			_ = os.Remove(pidFile)
		}()
	}

	// 7. Jendela native WebView2
	dataPath := filepath.Join(appDir, "cache", "webview2-data")
	_ = os.MkdirAll(dataPath, 0755)
	runWebView(appURL, dataPath)
}
