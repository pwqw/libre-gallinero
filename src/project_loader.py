# project_loader.py - Project loader
# Minimal module for loading project-specific code

def log(msg):
    """Escribe al serial de forma consistente"""
    print(f"[project] {msg}")
    try:
        import sys
        if hasattr(sys.stdout, 'flush'):
            sys.stdout.flush()
    except:
        pass

def load_project(project_name, cfg):
    """
    Load and run project-specific code (OPCIONAL)
    Si el módulo no existe, simplemente no lo carga y continúa.
    Esto permite que el setup inicial funcione sin los módulos del proyecto.
    """
    import gc
    
    log("=== Cargando proyecto ===")
    log(f"Proyecto: {project_name}")
    gc.collect()
    log(f"Memoria libre después de GC: {gc.mem_free()} bytes")
    
    try:
        if project_name == 'gallinero':
            log("Importando módulo gallinero...")
            import gallinero
            log("Módulo gallinero importado")
            log("Ejecutando gallinero.run()...")
            gallinero.run(cfg)
        elif project_name == 'heladera':
            log("Importando módulo heladera...")
            import heladera
            log("Módulo heladera importado")
            log("Ejecutando heladera.blink_led()...")
            heladera.blink_led()
        else:
            log(f"⚠ Proyecto desconocido: {project_name}")
            log("Proyectos disponibles: gallinero, heladera")
            log("Continuando sin cargar proyecto...")
    except ImportError as e:
        log(f"⚠ Módulo {project_name} no encontrado: {e}")
        log("Esto es normal durante el setup inicial.")
        log("El módulo se instalará durante el deploy por WiFi.")
        log("Sistema funcionando en modo básico (WiFi + WebREPL)")
    except Exception as e:
        log(f"✗ Error ejecutando proyecto {project_name}: {e}")
        import sys
        sys.print_exception(e)
        log("Continuando sin proyecto...")

