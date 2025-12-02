from backend.core.db.connection import get_connection

# ✅ 1. OBTENER ÚLTIMOS ACCESOS (Tráfico Reciente)
def obtener_ultimos_accesos():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT 
                TO_CHAR(a.fecha_hora, 'HH12:MI AM') as hora,
                v.placa,
                a.resultado,
                COALESCE(u.nombre, 'Sistema') as usuario
            FROM acceso a
            INNER JOIN vehiculo v ON a.id_vehiculo = v.id_vehiculo
            LEFT JOIN tmusuarios u ON a.id_vigilante = u.nu
            ORDER BY a.fecha_hora DESC
            LIMIT 7;
        """
        cursor.execute(query)
        accesos = cursor.fetchall()
        
        return [{"fecha_hora": r[0], "placa": r[1], "resultado": r[2], "vigilante": r[3]} for r in accesos]

    except Exception as ex:
        print(f"❌ Error en obtener_ultimos_accesos: {ex}")
        return []
    finally:
        if conn: conn.close()

# ✅ 2. TOTAL VEHICULOS REGISTRADOS
def contar_total_vehiculos():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM vehiculo;")
        return {"total": cur.fetchone()[0]}
    except: return {"total": 0}
    finally: conn.close()

# ✅ 3. TOTAL ALERTAS
def contar_alertas_activas():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM alerta;")
        return {"total": cur.fetchone()[0]}
    except: return {"total": 0}
    finally: conn.close()

# ✅ 4. BUSCAR PLACA
def buscar_placa_bd(placa):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT v.placa, v.tipo, v.color, p.nombre 
            FROM vehiculo v JOIN persona p ON v.id_persona = p.id_persona 
            WHERE v.placa = %s;
        """, (placa.upper(),))
        r = cur.fetchone()
        return {"placa": r[0], "tipo": r[1], "color": r[2], "propietario": r[3]} if r else None
    except: return None
    finally: conn.close()

# ✅ 5. OCUPACIÓN REAL (1000 Motos / 300 Carros)
def obtener_ocupacion_real():
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # NOTA: Usamos doble %% para escapar el % en Python
        sql = """
            SELECT 
                SUM(CASE WHEN v.tipo ILIKE '%%MOTO%%' THEN 1 ELSE 0 END),
                SUM(CASE WHEN v.tipo ILIKE '%%AUTO%%' OR v.tipo ILIKE '%%CAMIONETA%%' THEN 1 ELSE 0 END)
            FROM acceso a
            JOIN vehiculo v ON a.id_vehiculo = v.id_vehiculo
            WHERE a.hora_salida IS NULL;
        """
        cur.execute(sql)
        row = cur.fetchone()
        
        # Protección contra Nulos
        motos_occ = int(row[0]) if row and row[0] else 0
        carros_occ = int(row[1]) if row and row[1] else 0
        
        CAP_MOTOS = 1000
        CAP_CARROS = 300
        
        total_occ = motos_occ + carros_occ
        total_cap = CAP_MOTOS + CAP_CARROS
        porcentaje = round((total_occ / total_cap * 100), 1) if total_cap > 0 else 0
        
        return {
            "motos": {"ocupados": motos_occ, "total": CAP_MOTOS, "disp": CAP_MOTOS - motos_occ},
            "carros": {"ocupados": carros_occ, "total": CAP_CARROS, "disp": CAP_CARROS - carros_occ},
            "global": {"ocupados": total_occ, "total": total_cap, "disp": total_cap - total_occ, "pct": porcentaje}
        }
    except Exception as e:
        print("❌ Error ocupación:", e)
        return {
            "motos": {"ocupados": 0, "total": 1000, "disp": 1000},
            "carros": {"ocupados": 0, "total": 300, "disp": 300},
            "global": {"ocupados": 0, "total": 1300, "disp": 1300, "pct": 0}
        }
    finally:
        if conn: conn.close()