"""Minimal runner used only where pytest is unavailable: calls every test_* function."""
import importlib, sys, traceback
sys.path.insert(0, ".")
sys.modules.setdefault("pytest", type(sys)("pytest"))
class _Skip(Exception): pass
sys.modules["pytest"].skip = lambda msg="": (_ for _ in ()).throw(_Skip(msg))
passed = skipped = failed = 0
for mod in sys.argv[1:]:
    m = importlib.import_module(mod)
    for name in sorted(n for n in dir(m) if n.startswith("test_")):
        try:
            getattr(m, name)(); passed += 1; print("PASS", mod, name)
        except _Skip as e:
            skipped += 1; print("SKIP", mod, name, "-", e)
        except Exception:
            failed += 1; print("FAIL", mod, name); traceback.print_exc()
print(f"passed={passed} skipped={skipped} failed={failed}")
sys.exit(1 if failed else 0)
