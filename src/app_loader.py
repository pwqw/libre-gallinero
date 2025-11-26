# app_loader.py - App loader
# Carga y ejecuta la app configurada para esta plaquita NodeMCU

def log(msg):
    print(f"[app] {msg}")
    try:
        import sys
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
        log("Normal en setup inicial - deploy por WiFi")
    except Exception as e:
        log(f"✗ Error: {e}")
        import sys
        sys.print_exception(e)

