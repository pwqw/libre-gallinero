# app_loader.py - App loader
# Carga y ejecuta la app configurada para esta plaquita NodeMCU
import sys

def log(msg):
    print(f"[app] {msg}")
    try:
        if hasattr(sys.stdout, 'flush'):
            sys.stdout.flush()
    except:
        pass

def load_app(app_name, cfg):
    """
    Carga y ejecuta la app especificada.
    
    Cada app debe tener una función run(cfg) que implementa la lógica principal.
    """
    import gc
    log(f"App: {app_name}")
    gc.collect()
    
    try:
        if app_name == 'blink':
            import blink
            blink.run(cfg)
        elif app_name == 'gallinero':
            import gallinero
            gallinero.run(cfg)
        elif app_name == 'heladera':
            import heladera
            heladera.run(cfg)
        else:
            log(f"⚠ App desconocida: {app_name}")
    except ImportError as e:
        log(f"⚠ Módulo no encontrado: {e}")

        # Provide helpful diagnostic information
        try:
            import os
            root_files = os.listdir('/')

            # Check what's actually present
            has_app_dir = app_name in root_files

            if not has_app_dir:
                log(f"⚠ Directorio '{app_name}/' no existe en el ESP8266")
                log("💡 Solución: python3 tools/deploy_wifi.py " + app_name)
            else:
                log(f"⚠ Directorio existe pero import falló")
                log(f"💡 Prueba: python3 tools/deploy_wifi.py {app_name}")

        except Exception:
            pass  # Can't diagnose, continue anyway

    except Exception as e:
        log(f"✗ Error al cargar app: {e}")
        import sys
        sys.print_exception(e)

