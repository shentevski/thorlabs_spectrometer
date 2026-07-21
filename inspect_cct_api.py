"""
inspect_cct_api.py
==================
Dump the COMPLETE public API of the Thorlabs CCT-series spectrometer .NET
driver by reflection. Run this ONCE on the Windows PC that has the CCT SDK
installed, then send the printed output back so the wrapper can be built to
cover every available function (not just the handful in the example).

The hardware does NOT need to be connected -- this only reads metadata that is
baked into the managed assembly.

Usage (on the Windows PC):

    pip install pythonnet
    python inspect_cct_api.py            # auto-finds ./pyCCT/net48
    python inspect_cct_api.py C:\\path\\to\\net48   # or pass the folder

Tip: capture the output to a file you can paste back:

    python inspect_cct_api.py > cct_api_dump.txt
"""

import os
import sys
import clr  # from pythonnet

# Driver assembly name (no .dll extension) and the folder that holds it.
ASSEMBLY = "Thorlabs.ManagedDevice.CompactSpectrographDriver"
DEFAULT_DLL_DIR = os.path.abspath(os.path.join(os.getcwd(), "./pyCCT/net48"))


def _type_name(t):
    """Pretty, readable name for a .NET type, unwrapping Task<T>, Nullable<T>,
    arrays and other generics so the real argument/return types are visible."""
    if t is None:
        return "void"
    try:
        name = t.Name
    except Exception:
        return str(t)
    if getattr(t, "IsGenericType", False):
        base = name.split("`")[0]
        args = ", ".join(_type_name(a) for a in t.GetGenericArguments())
        return f"{base}<{args}>"
    return name


def _signature(m):
    params = ", ".join(f"{_type_name(p.ParameterType)} {p.Name}" for p in m.GetParameters())
    return f"{m.Name}({params}) -> {_type_name(m.ReturnType)}"


def dump(dll_dir):
    if dll_dir not in sys.path:
        sys.path.append(dll_dir)
    os.environ["PATH"] = dll_dir + os.pathsep + os.environ.get("PATH", "")
    clr.AddReference(os.path.join(dll_dir, ASSEMBLY))

    from System.Reflection import Assembly, BindingFlags

    asm = Assembly.LoadFrom(os.path.join(dll_dir, ASSEMBLY + ".dll"))
    print(f"# Assembly: {asm.FullName}\n")

    flags = BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly

    for t in sorted(asm.GetExportedTypes(), key=lambda x: x.FullName):
        kind = ("interface" if t.IsInterface else
                "enum" if t.IsEnum else
                "class")
        print(f"\n{'=' * 78}\n{kind.upper()}  {t.FullName}\n{'=' * 78}")

        if t.IsEnum:
            for name in t.GetEnumNames():
                print(f"    {name}")
            continue

        props = sorted(t.GetProperties(flags), key=lambda p: p.Name)
        if props:
            print("  -- Properties --")
            for p in props:
                rw = ("get/set" if p.CanRead and p.CanWrite else
                      "get" if p.CanRead else "set")
                print(f"    {_type_name(p.PropertyType)} {p.Name}  [{rw}]")

        # Hide property accessors and event add/remove from the method list.
        methods = sorted(
            (m for m in t.GetMethods(flags) if not m.IsSpecialName),
            key=lambda m: m.Name,
        )
        if methods:
            print("  -- Methods --")
            for m in methods:
                print(f"    {_signature(m)}")

        events = sorted(t.GetEvents(flags), key=lambda e: e.Name)
        if events:
            print("  -- Events --")
            for e in events:
                print(f"    {e.Name} : {_type_name(e.EventHandlerType)}")


if __name__ == "__main__":
    dll_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DLL_DIR
    print(f"# Reflecting over DLLs in: {dll_dir}\n")
    dump(dll_dir)
