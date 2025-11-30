import flet as ft
import sqlite3
import datetime
import os

# --- Lógica de Base de Datos y Negocio ---
class Database:
    def __init__(self):
        # Ruta compatible con Android y PC
        base_dir = os.path.expanduser("~")
        db_path = os.path.join(base_dir, "erp_empresas.db")
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Tabla Empresas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS empresas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                activa INTEGER DEFAULT 1
            )
        """)
        
        # Inicializar empresas por defecto si no existen
        cursor.execute("SELECT COUNT(*) FROM empresas")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO empresas (nombre) VALUES ('Empresa A')")
            cursor.execute("INSERT INTO empresas (nombre) VALUES ('Empresa B')")
        
        # Tabla Productos (Inventario)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER,
                nombre TEXT,
                stock INTEGER DEFAULT 0,
                precio_venta INTEGER,
                costo_unitario INTEGER
            )
        """)
        
        # Tabla Movimientos (Compras/Ventas Formales e Informales)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER,
                tipo TEXT,          -- 'venta' o 'compra'
                es_formal INTEGER,  -- 1 = Si (SII), 0 = No (Informal)
                fecha TEXT,
                producto_id INTEGER,
                cantidad INTEGER,
                monto_total INTEGER, -- Bruto
                detalle TEXT
            )
        """)
        self.conn.commit()

    # --- Gestión de Empresas ---
    def obtener_empresas(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM empresas WHERE activa = 1")
        return cursor.fetchall()
    
    def agregar_empresa(self, nombre):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO empresas (nombre) VALUES (?)", (nombre,))
        self.conn.commit()
        return cursor.lastrowid
    
    def actualizar_nombre_empresa(self, empresa_id, nuevo_nombre):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE empresas SET nombre = ? WHERE id = ?", (nuevo_nombre, empresa_id))
        self.conn.commit()
    
    def eliminar_empresa(self, empresa_id):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE empresas SET activa = 0 WHERE id = ?", (empresa_id,))
        self.conn.commit()

    # --- Gestión de Inventario ---
    def obtener_productos(self, empresa_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM productos WHERE empresa_id = ?", (empresa_id,))
        return cursor.fetchall()

    def agregar_producto(self, empresa_id, nombre, precio, costo):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO productos (empresa_id, nombre, precio_venta, costo_unitario, stock) VALUES (?, ?, ?, ?, 0)",
                       (empresa_id, nombre, precio, costo))
        self.conn.commit()

    # --- Motor de Transacciones (El Corazón del Sistema) ---
    def registrar_transaccion(self, empresa_id, tipo, es_formal, prod_id, cantidad, precio_unitario, detalle):
        cursor = self.conn.cursor()
        fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        monto_total = int(cantidad * precio_unitario)

        try:
            # 1. Registrar el movimiento financiero
            cursor.execute("""
                INSERT INTO movimientos (empresa_id, tipo, es_formal, fecha, producto_id, cantidad, monto_total, detalle)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (empresa_id, tipo, 1 if es_formal else 0, fecha, prod_id, cantidad, monto_total, detalle))

            # 2. Actualizar Inventario Automáticamente
            if tipo == 'compra':
                cursor.execute("UPDATE productos SET stock = stock + ? WHERE id = ?", (cantidad, prod_id))
            elif tipo == 'venta':
                cursor.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (cantidad, prod_id))

            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error transaction: {e}")
            return False

    # --- Contabilidad y Reportes ---
    def obtener_resumen(self, empresa_id):
        cursor = self.conn.cursor()
        # Obtener ventas y compras totales
        cursor.execute("SELECT tipo, monto_total FROM movimientos WHERE empresa_id = ?", (empresa_id,))
        data = cursor.fetchall()
        
        ventas = sum(x[1] for x in data if x[0] == 'venta')
        compras = sum(x[1] for x in data if x[0] == 'compra')
        return ventas, compras

    def reporte_sii(self, empresa_id):
        """Calcula IVA Débito y Crédito solo de movimientos FORMALES"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT tipo, monto_total FROM movimientos WHERE empresa_id = ? AND es_formal = 1", (empresa_id,))
        data = cursor.fetchall()

        # En Chile: Monto Bruto / 1.19 = Neto. Bruto - Neto = IVA.
        iva_debito = 0  # Lo que debo pagar por ventas
        iva_credito = 0 # Lo que tengo a favor por compras
        total_ventas_bruto = 0
        total_compras_bruto = 0

        for tipo, monto in data:
            neto = int(monto / 1.19)
            iva = monto - neto
            
            if tipo == 'venta':
                iva_debito += iva
                total_ventas_bruto += monto
            else:
                iva_credito += iva
                total_compras_bruto += monto
                
        return total_ventas_bruto, total_compras_bruto, iva_debito, iva_credito

# --- Interfaz Gráfica (Flet) ---
def main(page: ft.Page):
    page.title = "JEmpressa"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 400
    page.window_height = 800
    
    # Configurar icono de la aplicación
    if os.path.exists("assets/icon.png"):
        page.window_icon = "assets/icon.png"
    
    db = Database()
    empresa_actual = None # ID de la empresa seleccionada
    nombre_empresa_actual = None
    
    def seleccionar_empresa(id_emp, nombre):
        nonlocal empresa_actual, nombre_empresa_actual
        empresa_actual = id_emp
        nombre_empresa_actual = nombre
        page.title = f"JEmpressa - {nombre}"
        page.clean()
        cargar_interfaz_principal(nombre)
    
    # Modal Nueva Empresa
    txt_nueva_empresa = ft.TextField(label="Nombre de la Empresa", autofocus=True)
    
    def guardar_nueva_empresa(e):
        if txt_nueva_empresa.value:
            db.agregar_empresa(txt_nueva_empresa.value)
            txt_nueva_empresa.value = ""
            modal_nueva_empresa.open = False
            page.clean()
            page.add(vista_seleccion_empresa())
        page.update()
    
    def cerrar_modal_nueva_empresa(e):
        modal_nueva_empresa.open = False
        page.update()
    
    modal_nueva_empresa = ft.AlertDialog(
        modal=True,
        title=ft.Text("➕ Nueva Empresa"),
        content=txt_nueva_empresa,
        actions=[
            ft.TextButton("Cancelar", on_click=cerrar_modal_nueva_empresa),
            ft.ElevatedButton("Crear", on_click=guardar_nueva_empresa)
        ]
    )
    
    def abrir_modal_nueva_empresa():
        txt_nueva_empresa.value = ""
        modal_nueva_empresa.open = True
        if modal_nueva_empresa not in page.overlay:
            page.overlay.append(modal_nueva_empresa)
        page.update()
    
    def cerrar_modal(modal):
        modal.open = False
        page.update()
    
    # Vista Gestión de Empresas
    def abrir_gestion_empresas():
        empresas = db.obtener_empresas()
        lista_empresas = []
        
        for emp in empresas:
            txt_nombre = ft.TextField(value=emp[1], width=200)
            
            def crear_guardar(empresa_id, campo_texto):
                def guardar(e):
                    if campo_texto.value:
                        db.actualizar_nombre_empresa(empresa_id, campo_texto.value)
                        mostrar_snackbar("Empresa actualizada")
                return guardar
            
            def crear_eliminar(empresa_id):
                def eliminar(e):
                    db.eliminar_empresa(empresa_id)
                    abrir_gestion_empresas()
                return eliminar
            
            lista_empresas.append(
                ft.Container(
                    content=ft.Row([
                        txt_nombre,
                        ft.ElevatedButton("💾 Guardar", on_click=crear_guardar(emp[0], txt_nombre)),
                        ft.ElevatedButton("🗑️ Eliminar", on_click=crear_eliminar(emp[0]), bgcolor="red", color="white")
                    ], alignment=ft.MainAxisAlignment.START),
                    padding=10,
                    border=ft.border.all(1, "grey300"),
                    border_radius=10,
                    margin=5
                )
            )
        
        def volver(e):
            page.clean()
            page.add(vista_seleccion_empresa())
        
        page.clean()
        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.ElevatedButton("⬅️ Volver", on_click=volver),
                        ft.Text("Gestión de Empresas", size=20, weight="bold")
                    ], alignment=ft.MainAxisAlignment.START),
                    ft.Divider(),
                    ft.Column(lista_empresas, scroll=ft.ScrollMode.AUTO, expand=True)
                ], expand=True),
                padding=20,
                expand=True
            )
        )
        page.update()
    
    def mostrar_snackbar(mensaje):
        page.snack_bar = ft.SnackBar(ft.Text(mensaje))
        page.snack_bar.open = True
        page.update()

    # --- Vista de Selección de Empresa ---
    def vista_seleccion_empresa():
        empresas = db.obtener_empresas()
        
        def crear_click_empresa(emp_id, emp_nombre):
            def click(e):
                print(f"Click en empresa: {emp_nombre}")
                seleccionar_empresa(emp_id, emp_nombre)
            return click
        
        def click_nueva_empresa(e):
            print("Click en Nueva Empresa")
            abrir_modal_nueva_empresa()
        
        def click_gestionar(e):
            print("Click en Gestionar Empresas")
            abrir_gestion_empresas()
        
        botones_empresas = []
        iconos = ["🏪", "🏬", "🏢", "🏭", "🏛️"]
        
        for emp in empresas:
            idx = (emp[0] - 1) % len(iconos)
            botones_empresas.append(
                ft.ElevatedButton(
                    f"{iconos[idx]} {emp[1]}",
                    width=300,
                    on_click=crear_click_empresa(emp[0], emp[1])
                )
            )
        
        botones_empresas.append(
            ft.ElevatedButton(
                "➕ Nueva Empresa",
                width=300,
                on_click=click_nueva_empresa
            )
        )
        
        botones_empresas.append(
            ft.ElevatedButton(
                "⚙️ Gestionar Empresas",
                width=300,
                on_click=click_gestionar
            )
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Text("🏢", size=60),
                ft.Text("Selecciona tu Empresa", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("Gestiona inventario y contabilidad por separado", color="grey"),
                ft.Divider(),
            ] + botones_empresas, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20, scroll=ft.ScrollMode.AUTO),
            alignment=ft.alignment.center,
            expand=True,
            padding=20
        )

    # --- Componentes de la App Principal ---
    
    def cargar_interfaz_principal(nombre_empresa):
        
        # Variable para guardar la función de actualización
        actualizar_tab_ref = [None]
        
        # Variables para guardar referencias a funciones de modales
        abrir_modal_producto_ref = [None]
        abrir_modal_transaccion_ref = [None]
        
        # --- Modales (Formularios) - Definir PRIMERO ---
        
        # Modal Producto
        txt_prod_nom = ft.TextField(label="Nombre Producto")
        txt_prod_pre = ft.TextField(label="Precio Venta", keyboard_type="number")
        txt_prod_cos = ft.TextField(label="Costo Unitario", keyboard_type="number")
        
        def guardar_producto(e):
            if txt_prod_nom.value and txt_prod_pre.value:
                db.agregar_producto(empresa_actual, txt_prod_nom.value, int(txt_prod_pre.value), int(txt_prod_cos.value) if txt_prod_cos.value else 0)
                txt_prod_nom.value = ""
                txt_prod_pre.value = ""
                txt_prod_cos.value = ""
                modal_producto.open = False
                if actualizar_tab_ref[0]:
                    actualizar_tab_ref[0](1) # Recargar inventario
            page.update()

        def cerrar_modal_producto(e):
            modal_producto.open = False
            page.update()
        
        modal_producto = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nuevo Producto"),
            content=ft.Column([txt_prod_nom, txt_prod_pre, txt_prod_cos], tight=True),
            actions=[
                ft.TextButton("Cancelar", on_click=cerrar_modal_producto),
                ft.TextButton("Guardar", on_click=guardar_producto)
            ]
        )

        def abrir_modal_producto(e):
            txt_prod_nom.value = ""
            txt_prod_pre.value = ""
            txt_prod_cos.value = ""
            modal_producto.open = True
            page.overlay.append(modal_producto)
            page.update()

        # Modal Transacción
        dd_prod = ft.Dropdown(label="Producto", options=[])
        txt_cant = ft.TextField(label="Cantidad", keyboard_type="number", value="1")
        sw_formal = ft.Switch(label="Es Formal (Boleta/Factura)", value=True)
        btn_accion = ft.ElevatedButton("Registrar")
        
        def preparar_dd_productos():
            prods = db.obtener_productos(empresa_actual)
            dd_prod.options = [ft.dropdown.Option(key=p[0], text=f"{p[2]} (Stock: {p[3]})") for p in prods]
            if prods: 
                dd_prod.value = prods[0][0]
            else:
                dd_prod.value = None
            page.update()

        def guardar_transaccion(tipo):
            if dd_prod.value and txt_cant.value:
                try:
                    # Buscar precio del producto seleccionado
                    prods = db.obtener_productos(empresa_actual)
                    precio_u = 0
                    for p in prods:
                        if str(p[0]) == str(dd_prod.value):
                            # Si es venta usa precio venta, si es compra usa costo
                            precio_u = p[4] if tipo == 'venta' else p[5]
                            break
                    
                    if precio_u > 0:
                        db.registrar_transaccion(
                            empresa_actual, tipo, sw_formal.value, 
                            int(dd_prod.value), int(txt_cant.value), precio_u, 
                            f"{tipo.capitalize()} de mercadería"
                        )
                        modal_transaccion.open = False
                        if actualizar_tab_ref[0]:
                            actualizar_tab_ref[0](0) # Recargar dashboard
                        mostrar_snackbar(f"{tipo.capitalize()} registrada correctamente")
                    else:
                        mostrar_snackbar("Error: Producto no encontrado")
                except Exception as ex:
                    mostrar_snackbar(f"Error: {str(ex)}")
            else:
                mostrar_snackbar("Por favor completa todos los campos")
            page.update()

        def cerrar_modal_transaccion(e):
            modal_transaccion.open = False
            page.update()
        
        modal_transaccion = ft.AlertDialog(
            modal=True,
            title=ft.Text("Registrar Movimiento"),
            content=ft.Column([dd_prod, txt_cant, sw_formal], tight=True),
            actions=[
                ft.TextButton("Cancelar", on_click=cerrar_modal_transaccion),
                btn_accion
            ]
        )

        def abrir_modal_transaccion(tipo):
            prods = db.obtener_productos(empresa_actual)
            if not prods:
                # Mostrar diálogo de alerta
                def cerrar_dlg_info(e):
                    dlg_info.open = False
                    page.update()
                
                dlg_info = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("⚠️ Sin Productos"),
                    content=ft.Text("Primero debes agregar productos al inventario.\n\nVe a la pestaña 'Inventario' y presiona el botón '➕ Nuevo' para agregar tu primer producto."),
                    actions=[ft.TextButton("Entendido", on_click=cerrar_dlg_info)]
                )
                dlg_info.open = True
                page.overlay.append(dlg_info)
                page.update()
                return
                
            preparar_dd_productos()
            modal_transaccion.title.value = f"Registrar {tipo.capitalize()}"
            btn_accion.text = f"Confirmar {tipo.capitalize()}"
            btn_accion.on_click = lambda e: guardar_transaccion(tipo)
            
            # Color distintivo
            btn_accion.bgcolor = "green" if tipo == "venta" else "red"
            btn_accion.color = "white"
            
            modal_transaccion.open = True
            if modal_transaccion not in page.overlay:
                page.overlay.append(modal_transaccion)
            page.update()
        
        # Guardar referencias a las funciones de modales
        abrir_modal_producto_ref[0] = abrir_modal_producto
        abrir_modal_transaccion_ref[0] = abrir_modal_transaccion
        
        # Funciones de click (FUERA de build para que funcionen correctamente)
        def click_venta(e):
            print("Click en Nueva Venta")
            abrir_modal_transaccion("venta")
        
        def click_compra(e):
            print("Click en Nueva Compra")
            abrir_modal_transaccion("compra")
        
        def ir_inventario(e):
            print("Click en Ir a Inventario")
            actualizar_tab_ref[0](1)
        
        def click_nuevo_producto(e):
            print("Click en Nuevo Producto")
            abrir_modal_producto(e)
        
        # 1. Tablero Resumen (Dashboard)
        def build_dashboard():
            ventas, compras = db.obtener_resumen(empresa_actual)
            utilidad = ventas - compras
            prods = db.obtener_productos(empresa_actual)
            
            # Mensaje de bienvenida si no hay productos
            alerta_productos = []
            if not prods:
                alerta_productos.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Text("👋 ¡Bienvenido!", size=18, weight="bold"),
                            ft.Text("Para comenzar, agrega productos a tu inventario."),
                            ft.ElevatedButton(
                                "➕ Ir a Inventario",
                                on_click=ir_inventario,
                                bgcolor="green",
                                color="white"
                            )
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        bgcolor="amber100",
                        padding=20,
                        border_radius=10,
                        border=ft.border.all(2, "orange")
                    )
                )
            
            col = ft.Column(alerta_productos + [
                ft.Container(
                    content=ft.Column([
                        ft.Text("Utilidad Estimada", color="white70"),
                        ft.Text(f"${utilidad:,.0f}", size=30, weight="bold", color="white")
                    ]),
                    bgcolor="blue700", padding=20, border_radius=15, width=float("inf")
                ),
                ft.Row([
                    ft.Container(
                        content=ft.Column([
                            ft.Text("📈", size=30),
                            ft.Text("Ventas Totales"),
                            ft.Text(f"${ventas:,.0f}", weight="bold")
                        ]), bgcolor="green50", padding=15, border_radius=10, expand=True
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("📉", size=30),
                            ft.Text("Compras Totales"),
                            ft.Text(f"${compras:,.0f}", weight="bold")
                        ]), bgcolor="red50", padding=15, border_radius=10, expand=True
                    )
                ]),
                ft.Divider(),
                ft.Text("Accesos Rápidos", weight="bold"),
                ft.Row([
                    ft.ElevatedButton("Nueva Venta", on_click=click_venta, expand=True),
                    ft.ElevatedButton("Nueva Compra", on_click=click_compra, expand=True)
                ])
            ], spacing=20)
            
            return ft.Container(content=col, padding=20, expand=True)

        # 2. Inventario
        def build_inventario():
            prods = db.obtener_productos(empresa_actual)
            lista = ft.ListView(expand=True, spacing=10)
            
            for p in prods:
                # p = id, emp_id, nombre, stock, precio, costo
                valor_inventario = p[3] * p[5] # Stock * Costo
                lista.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Column([
                                ft.Text(p[2], weight="bold"), # Nombre
                                ft.Text(f"Precio: ${p[4]:,.0f}", size=12, color="grey")
                            ], expand=True),
                            ft.Column([
                                ft.Text(f"Stock: {p[3]}", weight="bold", color="blue" if p[3] > 5 else "red"),
                                ft.Text(f"Val: ${valor_inventario:,.0f}", size=12, color="grey")
                            ], alignment=ft.MainAxisAlignment.END)
                        ]),
                        bgcolor="white", padding=10, border_radius=10, border=ft.border.all(1, "grey200")
                    )
                )
            
            col = ft.Column([
                ft.Row([
                    ft.Text("Productos", size=20, weight="bold"),
                    ft.ElevatedButton("➕ Nuevo", on_click=click_nuevo_producto)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                lista
            ], expand=True)
            
            return ft.Container(content=col, padding=20, expand=True)

        # 3. Contabilidad SII
        def build_contabilidad():
            v_bruto, c_bruto, debito, credito = db.reporte_sii(empresa_actual)
            impuesto_pagar = debito - credito
            color_res = "red" if impuesto_pagar > 0 else "green"
            texto_res = "A Pagar (F29)" if impuesto_pagar > 0 else "Remanente"
            
            col = ft.Column([
                ft.Text("Contabilidad (Norma Chilena)", size=20, weight="bold"),
                ft.Text("Solo considera movimientos 'Formales'", size=12, color="grey", italic=True),
                ft.Divider(),
                ft.Container(
                    content=ft.Column([
                        ft.Text("IVA Débito (Ventas)", weight="bold"),
                        ft.Text(f"+ ${debito:,.0f}", color="red"),
                        ft.Divider(),
                        ft.Text("IVA Crédito (Compras)", weight="bold"),
                        ft.Text(f"- ${credito:,.0f}", color="green"),
                        ft.Divider(thickness=2),
                        ft.Row([
                            ft.Text(texto_res, weight="bold"),
                            ft.Text(f"${abs(impuesto_pagar):,.0f}", weight="bold", size=18, color=color_res)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    ]),
                    padding=20, bgcolor="white", border_radius=10, border=ft.border.all(1, "grey300")
                ),
                ft.Container(
                    content=ft.Text("Nota: El cálculo asume IVA 19% incluido en el monto total (Bruto).", size=12),
                    padding=10
                )
            ])
            
            return ft.Container(content=col, padding=20, expand=True)

        # 4. Perfil/Configuración
        def build_perfil():
            nonlocal nombre_empresa_actual
            empresas = db.obtener_empresas()
            
            txt_nombre_actual = ft.TextField(
                label="Nombre de esta Empresa",
                value=nombre_empresa_actual,
                width=300
            )
            
            def guardar_nombre_empresa(e):
                if txt_nombre_actual.value:
                    db.actualizar_nombre_empresa(empresa_actual, txt_nombre_actual.value)
                    nombre_empresa_actual = txt_nombre_actual.value
                    page.appbar.title.value = nombre_empresa_actual
                    mostrar_snackbar("Nombre actualizado correctamente")
            
            # Lista de todas las empresas
            lista_empresas_items = []
            for emp in empresas:
                es_actual = emp[0] == empresa_actual
                lista_empresas_items.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(emp[1], weight="bold" if es_actual else None, size=16),
                            ft.Text("(Actual)" if es_actual else "", color="blue", italic=True)
                        ]),
                        bgcolor="blue50" if es_actual else "white",
                        padding=10,
                        border_radius=8,
                        border=ft.border.all(2 if es_actual else 1, "blue" if es_actual else "grey300"),
                        on_click=lambda e, id=emp[0], nom=emp[1]: seleccionar_empresa(id, nom) if not es_actual else None
                    )
                )
            
            col = ft.Column([
                ft.Text("⚙️ Configuración", size=24, weight="bold"),
                ft.Divider(),
                
                # Sección empresa actual
                ft.Text("Empresa Actual", size=18, weight="bold"),
                ft.Container(
                    content=ft.Column([
                        txt_nombre_actual,
                        ft.ElevatedButton(
                            "💾 Guardar Cambios",
                            on_click=guardar_nombre_empresa,
                            width=300
                        )
                    ]),
                    padding=15,
                    bgcolor="white",
                    border_radius=10,
                    border=ft.border.all(1, "grey300")
                ),
                
                ft.Divider(),
                
                # Todas las empresas
                ft.Text("Todas las Empresas", size=18, weight="bold"),
                ft.Text("Toca una empresa para cambiar", size=12, color="grey"),
                ft.Column(lista_empresas_items, spacing=10),
                
                ft.Divider(),
                
                # Botones de acción
                ft.ElevatedButton(
                    "➕ Agregar Nueva Empresa",
                    on_click=lambda e: abrir_modal_nueva_empresa_desde_perfil(),
                    width=300
                ),
                ft.ElevatedButton(
                    "🗑️ Gestionar Empresas",
                    on_click=lambda e: abrir_gestion_empresas(),
                    width=300,
                    bgcolor="orange",
                    color="white"
                )
            ], scroll=ft.ScrollMode.AUTO)
            
            return ft.Container(content=col, padding=20, expand=True)
        
        def abrir_modal_nueva_empresa_desde_perfil():
            txt_nueva_emp = ft.TextField(label="Nombre de la Nueva Empresa", autofocus=True)
            
            def cerrar_temp(e):
                modal_temp.open = False
                page.update()
            
            def guardar(e):
                if txt_nueva_emp.value:
                    db.agregar_empresa(txt_nueva_emp.value)
                    modal_temp.open = False
                    if actualizar_tab_ref[0]:
                        actualizar_tab_ref[0](3)  # Recargar perfil
                page.update()
            
            modal_temp = ft.AlertDialog(
                modal=True,
                title=ft.Text("➕ Nueva Empresa"),
                content=txt_nueva_emp,
                actions=[
                    ft.TextButton("Cancelar", on_click=cerrar_temp),
                    ft.ElevatedButton("Crear", on_click=guardar)
                ]
            )
            
            modal_temp.open = True
            page.overlay.append(modal_temp)
            page.update()

        # --- Navegación ---
        tabs_content = ft.Container(expand=True)
        tab_actual = [0]  # Lista para permitir modificación en lambda
        
        def actualizar_tab(index):
            tab_actual[0] = index
            tabs_content.content = None
            if index == 0: tabs_content.content = build_dashboard()
            elif index == 1: tabs_content.content = build_inventario()
            elif index == 2: tabs_content.content = build_contabilidad()
            elif index == 3: tabs_content.content = build_perfil()
            actualizar_botones_nav()
            page.update()
        
        # Guardar la referencia
        actualizar_tab_ref[0] = actualizar_tab

        def actualizar_botones_nav():
            for i, btn in enumerate([btn_resumen, btn_inventario, btn_contabilidad, btn_perfil]):
                btn.bgcolor = "blue" if i == tab_actual[0] else None
                btn.color = "white" if i == tab_actual[0] else None

        btn_resumen = ft.ElevatedButton("📊 Resumen", on_click=lambda e: actualizar_tab(0), expand=True)
        btn_inventario = ft.ElevatedButton("📦 Inventario", on_click=lambda e: actualizar_tab(1), expand=True)
        btn_contabilidad = ft.ElevatedButton("🧮 Contabilidad", on_click=lambda e: actualizar_tab(2), expand=True)
        btn_perfil = ft.ElevatedButton("⚙️ Perfil", on_click=lambda e: actualizar_tab(3), expand=True)
        
        nav_bar = ft.Row([
            btn_resumen,
            btn_inventario,
            btn_contabilidad,
            btn_perfil
        ], spacing=5)

        # Botón para salir/cambiar empresa
        btn_salir = ft.ElevatedButton("🔙 Cambiar", on_click=lambda e: (page.clean(), page.add(vista_seleccion_empresa())))

        page.appbar = ft.AppBar(
            title=ft.Text(nombre_empresa),
            bgcolor="blue", color="white",
            actions=[btn_salir]
        )
        
        page.add(tabs_content, nav_bar)
        actualizar_botones_nav()
        actualizar_tab(0)

    # Iniciar App
    page.add(vista_seleccion_empresa())

if __name__ == "__main__":
    ft.app(target=main)