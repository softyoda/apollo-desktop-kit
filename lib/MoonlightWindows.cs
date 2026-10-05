using System;
using System.Text;
using System.Runtime.InteropServices;
public static class MoonlightWindows {
    [DllImport("user32.dll", EntryPoint="GetWindowLongPtrW")] static extern IntPtr GetWindowLongPtr(IntPtr h,int index);
    [DllImport("user32.dll", EntryPoint="SetWindowLongPtrW")] static extern IntPtr SetWindowLongPtr(IntPtr h,int index,IntPtr value);
    public static bool Borderless(IntPtr h,int x,int y,int width,int height) {
        // Real borderless fullscreen placement, without injected keyboard input or focus dependency.
        long style = GetWindowLongPtr(h,-16).ToInt64();
        style &= ~(0x00C00000L | 0x00040000L | 0x00010000L | 0x00020000L);
        style |= 0x80000000L;
        SetWindowLongPtr(h,-16,new IntPtr(style));
        return SetWindowPos(h,IntPtr.Zero,x,y,width,height,0x0074);
    }
    public delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc cb, IntPtr l);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    public static int Owner(IntPtr h) { uint pid; GetWindowThreadProcessId(h,out pid); return (int)pid; }
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int w, int height, uint flags);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern IntPtr SetThreadDpiAwarenessContext(IntPtr context);
    [StructLayout(LayoutKind.Sequential)] public struct Rect { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out Rect rect);
    public static IntPtr FindStream(int pid) {
        IntPtr found = IntPtr.Zero;
        EnumWindows(delegate(IntPtr h, IntPtr l) {
            uint owner; GetWindowThreadProcessId(h, out owner);
            if (owner != pid || !IsWindowVisible(h)) return true;
            var name = new StringBuilder(256); GetClassName(h, name, name.Capacity);
            if (name.ToString().StartsWith("SDL")) { found = h; return false; }
            return true;
        }, IntPtr.Zero);
        return found;
    }
}