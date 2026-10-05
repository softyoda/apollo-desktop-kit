using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public static class DisplayControl {
 [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] public struct Mode {
  [MarshalAs(UnmanagedType.ByValTStr,SizeConst=32)] public string name;
  public ushort spec,driver,size,extra; public uint fields;
  public int x,y; public uint orientation,fixedOutput;
  public short color,duplex,yres,tt,collate;
  [MarshalAs(UnmanagedType.ByValTStr,SizeConst=32)] public string form;
  public ushort logPixels; public uint bits,width,height,flags,freq,icmMethod,icmIntent,media,dither,reserved1,reserved2,panningWidth,panningHeight;
 }
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern bool EnumDisplaySettings(string name,int index,ref Mode mode);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int ChangeDisplaySettingsEx(string name,ref Mode mode,IntPtr hwnd,uint flags,IntPtr param);
 [DllImport("user32.dll",CharSet=CharSet.Unicode,EntryPoint="ChangeDisplaySettingsExW")] static extern int CommitDisplays(IntPtr name,IntPtr mode,IntPtr hwnd,uint flags,IntPtr param);
 public static void Move(string name,int x,int y) {
  var m=Current(name); m.x=x; m.y=y; m.fields=0x20;
  int r=ChangeDisplaySettingsEx(name,ref m,IntPtr.Zero,2,IntPtr.Zero);
  if(r!=0) throw new Exception("Display position test failed: "+r);
  r=ChangeDisplaySettingsEx(name,ref m,IntPtr.Zero,0x10000001,IntPtr.Zero);
  if(r!=0) throw new Exception("Display position staging failed: "+r);
 }
 public static void Commit() { int r=CommitDisplays(IntPtr.Zero,IntPtr.Zero,IntPtr.Zero,0,IntPtr.Zero); if(r!=0) throw new Exception("Display commit failed: "+r); }
 public static Mode Current(string name) { var m = NewMode(); if (!EnumDisplaySettings(name,-1,ref m)) throw new Exception("Display not found: " + name); return m; }
 static Mode NewMode() { var m = new Mode(); m.size=(ushort)Marshal.SizeOf(typeof(Mode)); return m; }
 public static bool HasMode(string name,uint w,uint h,uint hz) { var m=NewMode(); for(int i=0;EnumDisplaySettings(name,i,ref m);i++) if(m.width==w && m.height==h && m.freq==hz) return true; return false; }
 public static void Set(string name,uint w,uint h,uint hz) {
  var m=Current(name); m.width=w; m.height=h; m.freq=hz; m.fields=0x580000;
  int result=ChangeDisplaySettingsEx(name,ref m,IntPtr.Zero,2,IntPtr.Zero);
  if(result!=0) throw new Exception("Windows mode test failed: "+result);
  result=ChangeDisplaySettingsEx(name,ref m,IntPtr.Zero,0,IntPtr.Zero);
  if(result!=0) throw new Exception("Windows mode change failed: "+result);
 }
 [StructLayout(LayoutKind.Sequential)] public struct TimingExtra {
  public uint flag; public ushort rr; public uint rrx1k,aspect; public ushort rep; public uint status;
  [MarshalAs(UnmanagedType.ByValArray,SizeConst=40)] public byte[] name;
 }
 [StructLayout(LayoutKind.Sequential)] public struct Timing {
  public ushort hv,hb,hfp,hsw,ht; public byte hp;
  public ushort vv,vb,vfp,vsw,vt; public byte vp;
  public ushort interlaced; public uint pclk; public TimingExtra extra;
 }
 [StructLayout(LayoutKind.Sequential)] public struct TimingInput { public uint version,width,height; public float rr; public uint flags,tvFormat,scaling,type; }
 [StructLayout(LayoutKind.Sequential)] public struct Custom {
  public uint version,width,height,depth,format;
  public float x,y,w,h,xRatio,yRatio;
  public Timing timing; public uint flags;
 }
 [DllImport("nvapi64.dll",EntryPoint="nvapi_QueryInterface",CallingConvention=CallingConvention.Cdecl)] static extern IntPtr Query(uint id);
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate int Init();
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate int GetId([MarshalAs(UnmanagedType.LPStr)]string name,out uint id);
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate int GetTiming(uint id,ref TimingInput input,out Timing timing);
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate int EnumCustom(uint id,uint index,ref Custom mode);
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate int TryCustom([In]uint[] ids,uint count,[In]Custom[] modes);
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate int SaveCustom([In]uint[] ids,uint count,uint outputOnly,uint monitorOnly);
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate int Revert([In]uint[] ids,uint count);
 static T Fn<T>(uint id) { var p=Query(id); if(p==IntPtr.Zero) throw new Exception("NVAPI function unavailable: "+id); return (T)(object)Marshal.GetDelegateForFunctionPointer(p,typeof(T)); }
 static void Check(int status,string operation) { if(status!=0) throw new Exception(operation+" NVAPI status="+status); }
 static uint Id(string name) { Check(Fn<Init>(0x0150e828)(),"Initialize"); uint id; Check(Fn<GetId>(0xae457190)(name,out id),"GetDisplayId"); return id; }
 public static string Probe(string name) {
  uint id=Id(name); var lines=new List<string>(); lines.Add("NVIDIA display id="+id+"; custom struct="+Marshal.SizeOf(typeof(Custom))+"; timing="+Marshal.SizeOf(typeof(Timing)));
  for(uint i=0;i<100;i++) { var c=new Custom(); c.version=(uint)Marshal.SizeOf(typeof(Custom))|0x10000;
   int status=Fn<EnumCustom>(0xa2072d59)(id,i,ref c); if(status==-7) break; Check(status,"EnumCustom"); lines.Add(c.width+"x"+c.height+" @ "+c.timing.extra.rr);
  } return string.Join("\n",lines);
 }
 public static void EnsureCustom(string name,uint width,uint height,uint hz) {
  if(HasMode(name,width,height,hz)) return;
  uint id=Id(name); var ids=new uint[]{id};
  var input=new TimingInput { version=(uint)Marshal.SizeOf(typeof(TimingInput))|0x10000,width=width,height=height,rr=hz,type=6 };
  Timing timing; Check(Fn<GetTiming>(0x175167e9)(id,ref input,out timing),"GetTiming CVT-RB");
  var custom=new Custom { version=(uint)Marshal.SizeOf(typeof(Custom))|0x10000,width=width,height=height,depth=32,format=21,w=1,h=1,xRatio=1,yRatio=1,timing=timing };
  try {
   Check(Fn<TryCustom>(0x1f7db630)(ids,1,new Custom[]{custom}),"TryCustomDisplay");
   Check(Fn<SaveCustom>(0x49882876)(ids,1,1,1),"SaveCustomDisplay");
  } finally { Check(Fn<Revert>(0xcbbd40f0)(ids,1),"RevertCustomDisplayTrial"); }
 }
}
