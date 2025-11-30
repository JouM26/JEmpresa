# JEmpressa 🏢

Sistema ERP para gestión empresarial multi-empresa. Administra inventario, ventas, compras y contabilidad de múltiples empresas desde una sola aplicación.

## 🚀 Características

- 📊 Dashboard con resumen financiero
- 📦 Gestión de inventario por empresa
- 🧮 Contabilidad con cálculo de IVA (Chile)
- 🏢 Soporte para múltiples empresas
- ⚙️ Configuración personalizable
- 💾 Base de datos SQLite local

## 📱 Instalación

### En PC (Windows/Mac/Linux)

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la aplicación
python main.py
```

### Compilar para Android

```bash
# Instalar flet
pip install flet

# Compilar APK
flet build apk

# El APK estará en: build/apk/JEmpressa.apk
```

### Compilar para iOS

```bash
# Requiere Mac con Xcode
flet build ipa
```

## 🎨 Logo Personalizado

El logo de la aplicación se encuentra en `assets/icon.png`. Para regenerarlo:

```bash
python create_logo.py
```

## 📝 Uso

1. **Selecciona o crea una empresa**
2. **Gestiona productos** - Agrega productos con precio y costo
3. **Registra ventas y compras** - Formales (con boleta/factura) o informales
4. **Revisa contabilidad** - Calcula automáticamente el IVA a pagar
5. **Configura tu perfil** - Cambia nombres de empresas o agrega nuevas

## 🗂️ Estructura

```
JEmpresa/
├── main.py              # Aplicación principal
├── create_logo.py       # Script para generar logos
├── requirements.txt     # Dependencias
├── pyproject.toml      # Configuración de Flet
├── assets/             # Logos e íconos
│   └── icon.png
└── README.md
```

## 📄 Licencia

Ver archivo LICENSE

---

Desarrollado con ❤️ usando Flet
