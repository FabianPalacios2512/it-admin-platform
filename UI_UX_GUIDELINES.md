# UI/UX & Design System Guidelines - AdminInfra

**MANDATORY RULES FOR AI AGENTS & DEVELOPERS**
This document serves as the absolute source of truth for the UI/UX architecture of the AdminInfra application. Any new component, view, or module **must strictly adhere** to these guidelines. Do not deviate.

---

## 1. Filosofía Global de Diseño (AdminInfra)
**Estilo Base:** "Microsoft Fluent UI" / Entra ID Design Language.
**Tema:** Light Mode estricto. Diseño corporativo, de grado empresarial, limpio y altamente minimalista.

* **Borderless (Sin cajas cerradas):** 
  - **PROHIBIDO** envolver componentes principales (como el data grid de tablas o la zona de filtros) en `divs` con bordes gruesos (`border-2`, `border-gray-300`, etc.) o sombras pesadas.
  - La arquitectura debe ser abierta y fluida. Utiliza el espacio en blanco (paddings/margins generosos) y fondos muy sutiles (ej. `bg-gray-50`) para crear la jerarquía visual, no cajas delimitadas.

---

## 2. Estándar de Modales (Single Source of Truth)
**Obligatoriedad:** Todo modal nuevo o refactorizado **DEBE** usar el componente envoltorio `<BaseModal>` (o `<ModalWrapper>`). Queda estrictamente **PROHIBIDO** crear o maquetar modales desde cero en los componentes hijos.

* **Estándar del Overlay (Backdrop Suave):** El fondo oscuro NUNCA debe ocultar el contenido de la aplicación; debe ser un velo muy sutil. Usar EXCLUSIVAMENTE `fixed inset-0 z-50 flex items-center justify-center bg-gray-900/20 backdrop-blur-[2px]`. Queda totalmente PROHIBIDO usar opacidades altas (como /50 o /70).
* **Sobriedad de Color (Escala de Grises Estricta):** 
  - **Textos:** Todo el texto (títulos, descripciones, listas, alertas) debe usar estrictamente la escala de grises (ej. `text-gray-900` para títulos, `text-gray-600` para cuerpos). NUNCA usar textos de colores (naranjas, rojos, verdes, azules) para el contenido.
  - **Contenedores Internos:** Las alertas o tarjetas informativas NUNCA deben tener fondos de colores llamativos (prohibido `bg-yellow-50`, `bg-red-50`, etc.). Para resaltar una alerta, usar un borde sutil gris (`border border-gray-200`) o un fondo gris ultraclaro (`bg-gray-50`) con un ícono neutro.
  - **Excepción Única:** Los únicos elementos que tienen permitido usar colores corporativos fuertes son los **Botones de Acción** (ej. `bg-blue-600` para primarias, `bg-red-600` para acciones destructivas).
* **Estructura del Contenedor (Anatomía Inmutable):** Fondo blanco, ancho máximo fijo (`max-w-lg` o `max-w-md`), bordes redondeados (`rounded-xl`), sombra (`shadow-lg`), borde muy sutil (`border border-gray-100`) y overflow oculto (`overflow-hidden`).
* **Cabecera (Header):**
  - **Padding/Bordes:** `px-6 py-4 border-b border-gray-100`.
  - **Tipografía de Títulos:** Siempre en formato "Sentence case" o "Title Case" (ej. "Restablecer contraseña"). **PROHIBIDO** el uso de MAYÚSCULAS sostenidas en los títulos. Peso exacto: `text-lg font-semibold text-gray-900`.
  - **Botón Cerrar ('X'):** Posición absoluta a la derecha (`absolute right-6 top-4`), estilo `text-gray-400 hover:text-gray-600`.
* **Cuerpo (Body):** Padding estandarizado de `p-6` para todo el contenido interior, con texto default `text-gray-600 text-sm`.
* **Footer de Botones:** `px-6 py-4 bg-gray-50 border-t border-gray-100 flex justify-end gap-3`. El botón de "Cancelar" siempre debe ir a la izquierda (estilo outline o solo texto gris), y el botón de "Acción" principal a la derecha (estilo sólido con el color de la intención, ej. `bg-blue-600` o `bg-red-600`).

---

## 3. Estándar de Tablas de Datos (Data Grids)
Las tablas deben sentirse ligeras y no ahogar al usuario con saturación de líneas y contenedores.

* **Contención de Ancho (Max-Width):** Las vistas principales de tablas deben estar envueltas en un contenedor centrado (ej. `max-w-7xl mx-auto w-full`) para evitar que la interfaz se estire infinitamente y pierda legibilidad en monitores ultrawide.
* **Filas Fluidas (Cero bordes exteriores):**
  - La tabla no debe tener un borde exterior encapsulante que la encierre por los cuatro lados.
  - Usa únicamente un borde inferior muy tenue (`border-b border-gray-100`) para separar las filas entre sí.
  - Al pasar el cursor por una fila de datos, aplica un efecto sutil `hover:bg-gray-50`.
* **Buscador y Filtros (Layout):**
  - El input de búsqueda de la tabla debe ir alineado a la **derecha**.
  - Debe estar ubicado exactamente en la misma fila horizontal donde se encuentran los tabs de filtrado principales (Todos | Activos | Bloqueados | etc.) que estarán alineados a la izquierda. No apilar en múltiples filas a menos que sea en dispositivos móviles.
* **Acciones de Fila (Kebab Menu):** Las acciones individuales de cada registro (ej. Editar, Ver Detalles) siempre van ocultas dentro de un menú de tres puntos (Kebab / Context Menu) en la celda del extremo derecho de la fila. Evitar la saturación visual llenando de botones cada fila.
* **Acciones Masivas (Command Bar):** Cuando el usuario selecciona una o varias filas (checkboxes), debe aparecer una barra de comandos plana en la parte superior de la tabla. Esta barra **no debe tener bordes ni usar cajas azules pesadas**; debe sentirse como una cinta de acciones nativa y minimalista que solo muestra los botones habilitados para las filas seleccionadas.
