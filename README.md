# Live Wallpaper Engine

**Bring your desktop to life.** ✨

Live Wallpaper Engine is a Windows desktop application designed to make your desktop more dynamic with live wallpapers. It provides a simple way to launch the wallpaper engine, choose wallpapers from the system tray, and troubleshoot animation issues.

## ✨ Features

- 🖥️ **Live Wallpapers** — Give your Windows desktop a dynamic look.
- 🎨 **Wallpaper Selection** — Choose your preferred wallpaper through the system tray menu.
- 🛠️ **Compatibility Mode** — Toggle compatibility mode to troubleshoot stuck or unresponsive wallpapers.
- ⚡ **Simple Launching** — Start the application using the included batch script.
- 🪟 **Windows Desktop Support** — Built for the Windows desktop environment.

## 📋 Requirements

- Windows 10 or Windows 11
- `install_and_run.bat`
- `livewallpaper.py`
- Any additional dependencies required by the project

## 📥 Installation & Setup

Follow these steps to get Live Wallpaper Engine running on your PC.

### Step 1: Download the Project

Download the repository as a ZIP file from GitHub and extract it to a folder on your computer.

Alternatively, clone the repository using Git:

```bash
git clone https://github.com/nitikash4-svg/Live-Wallpaper-Engine.git
```



### Step 2: Keep Both Files in the Same Folder

Make sure `install_and_run.bat` and `livewallpaper.py` are located in the **same directory**.

Your folder should look like this:

```text
Live-Wallpaper-Engine/
├── install_and_run.bat
├── livewallpaper.py
└── README.md
```

Other project files and dependencies may also be present.

**Important:** Do not separate `install_and_run.bat` and `livewallpaper.py` into different folders.

### Step 3: Run the Application

1. Open the project folder.
2. Double-click `install_and_run.bat`.
3. Allow the script to complete its installation and startup steps.
4. Look for the Live Wallpaper Engine icon in the Windows system tray, near the clock.

Your wallpaper engine should now be running.

## 🎨 How to Change Your Wallpaper

You can select wallpapers directly from the system tray.

1. Locate the Live Wallpaper Engine icon near the Windows taskbar clock.
2. Right-click the icon.
3. Select **Choose Wallpaper** from the context menu.
4. Choose the wallpaper you want to use from the available options.

Your selected wallpaper should appear on your desktop.

**Tip:** If you cannot see the icon, check the hidden system tray icons by clicking the `^` arrow near the clock.

## 🛠️ Troubleshooting

### 1. Wallpaper Is Stuck or Not Animating

If your wallpaper freezes, gets stuck, or stops moving, try switching Compatibility Mode.

1. Locate the application icon in the system tray.
2. Right-click the icon.
3. Find **Run in Compatible Mode**.
4. If the option is enabled, turn it off. If it is disabled, turn it on.
5. Check whether the wallpaper works correctly.

If the problem persists, toggle the option back to its previous state and test again.

### 2. Application Is Not Starting

If the application does not launch:

- Make sure `install_and_run.bat` and `livewallpaper.py` are in the same folder.
- Run `install_and_run.bat` again.
- Check for errors displayed in the command window.
- Verify that the required dependencies are installed.

### 3. System Tray Icon Is Missing

- Check the hidden icons section of the Windows system tray.
- Wait for the startup process to finish.
- If the application is not running, launch it again using `install_and_run.bat`.

### 4. Wallpaper Still Does Not Work

If none of the above steps resolve the issue:

- Try switching Compatibility Mode on or off.
- Restart the wallpaper engine.
- Check whether the problem occurs with another available wallpaper.
- Report the issue with your Windows version and any relevant error messages.

## 📂 Project Structure

The main files required to launch the application are:

| File | Purpose |

| `install_and_run.bat` | Starts the installation and launch process |
| `livewallpaper.py` | Python application entry point |
| `README.md` | Project documentation |

Additional files may be required depending on the implementation.

## 🗺️ Future Improvements

Potential improvements for future versions include:

- [ ] Expanded wallpaper library
- [ ] More wallpaper customization options
- [ ] Improved performance and resource management
- [ ] Enhanced compatibility and error handling
- [ ] Improved user interface and settings

These are potential enhancements and may not be available in the current version.

## 🤝 Contributing

Contributions, suggestions, and bug reports are welcome.

1. Fork this repository.
2. Create a branch for your changes.
3. Make and test your improvements.
4. Submit a pull request describing your changes.

## 🐛 Reporting Issues

If you encounter a bug, open an issue in the GitHub repository and include:

- Windows version
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Relevant error messages or screenshots

## 📜 License

A license has not yet been specified.

Before distributing this project as open source, add a suitable license file to clarify how others may use, modify, and redistribute the code.

## 👨‍💻 Author

**Developer:** Nitikash Gorai

**GitHub:** [nitikash4-svg]([https://github.com/YOUR-USERNAME](https://github.com/nitikash4-svg))

---

If you like this project, consider giving the repository a ⭐ on GitHub!

**Made with curiosity. Built to bring desktops to life.** 🚀
