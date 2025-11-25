# project_loader.py - Project loader
def log(msg):
    print(f"[project] {msg}")
    try:
        import sys
        if hasattr(sys.stdout, 'flush'):
            sys.stdout.flush()
    except:
        pass

def load_project(project_name, cfg):
    import gc
    log(f"Proyecto: {project_name}")
    gc.collect()
    
    try:
        if project_name == 'gallinero':
            import gallinero
            gallinero.run(cfg)
        elif project_name == 'heladera':
            import heladera
            heladera.blink_led()
        else:
            log(f"⚠ Proyecto desconocido: {project_name}")
    except ImportError as e:
        log(f"⚠ Módulo no encontrado: {e}")
        log("Normal en setup inicial - deploy por WiFi")
    except Exception as e:
        log(f"✗ Error: {e}")
        import sys
        sys.print_exception(e)
