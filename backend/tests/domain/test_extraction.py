"""
Tests del núcleo determinista de extracción (M2, dominio puro).

Contrato: lo numérico sale por regex con su span; lo ausente NO se inventa (None);
y la extracción es determinista (mismo texto -> mismo valor + mismo span).
"""
from app.domain.extraction import (
    extract_salary,
    extract_start_date,
    extract_end_date,
    extract_weekly_hours,
    extract_termination,
    extract_employee_name,
    extract_employee_doc,
    extract_auxilio_transporte,
    extract_salario_variable,
    extract_employer,
    extract_role,
)


_CONTRATO_HG = (
    "Entre los suscritos, HURTADO GANDINI & ASOCIADOS SAS, sociedad identificada con\n"
    "NIT 900.456.789-3, domiciliada en Cali, y JUAN PEREZ, identificado con cedula.\n"
    "El trabajador desempenara el cargo de Asesora de Compliance Laboral, realizando\n"
    "actividades de revision."
)


def test_employer_determinista_nombre_y_nit():
    ex = extract_employer(_CONTRATO_HG)
    assert ex is not None
    assert ex.value["name"] == "HURTADO GANDINI & ASOCIADOS SAS"
    assert ex.value["nit"] == "900.456.789-3"
    assert ex.span.text  # tiene cita


def test_employer_none_si_no_hay_estructura():
    # Sin "Entre los suscritos, X, sociedad/NIT" -> None (cae al LLM).
    assert extract_employer("Contrato laboral sin encabezado de partes.") is None


def test_role_determinista_hasta_la_coma():
    ex = extract_role(_CONTRATO_HG)
    assert ex is not None
    assert ex.value == "Asesora de Compliance Laboral"


def test_role_none_si_no_dice_cargo_de():
    assert extract_role("El puesto sera ejercido por el trabajador.") is None


def test_salario_con_separadores_se_extrae_con_span():
    text = "El trabajador devengara un salario mensual: 2.500.000 pesos."
    ex = extract_salary(text)
    assert ex is not None
    assert ex.value["amount"] == 2500000
    assert ex.value["periodicity"] == "mensual"
    # El span incluye el keyword de contexto para que la cita sea legible.
    assert text[ex.span.start:ex.span.end] == ex.span.text
    assert "2.500.000" in ex.span.text
    assert len(ex.span.text) >= 15


def test_salario_con_signo_pesos_y_periodicidad_quincenal():
    text = "Salario quincenal de $1.200.000 pagaderos."
    ex = extract_salary(text)
    assert ex is not None
    assert ex.value["amount"] == 1200000
    assert ex.value["periodicity"] == "quincenal"


def test_campo_ausente_devuelve_none_sin_inventar():
    # No hay 'salario' ni fechas ni horas -> los extractores no afirman nada.
    text = "Las partes acuerdan las clausulas generales del presente documento."
    assert extract_salary(text) is None
    assert extract_start_date(text) is None
    assert extract_end_date(text) is None
    assert extract_weekly_hours(text) is None


def test_extraccion_de_salario_es_determinista():
    text = "Clausula tercera. Salario mensual de 3.000.000 m/cte."
    primero = extract_salary(text)
    segundo = extract_salary(text)
    assert primero is not None and segundo is not None
    assert primero.value == segundo.value
    assert (primero.span.start, primero.span.end) == (segundo.span.start, segundo.span.end)
    assert primero.span.text == segundo.span.text


def test_fechas_inicio_y_fin_en_palabras_a_iso():
    text = ("El contrato regira a partir del 1 de febrero de 2024 "
            "hasta el 31 de enero de 2025.")
    inicio = extract_start_date(text)
    fin = extract_end_date(text)
    assert inicio is not None and inicio.value == "2024-02-01"
    assert fin is not None and fin.value == "2025-01-31"
    assert text[inicio.span.start:inicio.span.end] == inicio.span.text


def test_jornada_en_palabras_y_en_digitos():
    en_palabras = extract_weekly_hours("Cumplira una jornada de cuarenta y ocho horas semanales.")
    assert en_palabras is not None and en_palabras.value == 48
    en_digitos = extract_weekly_hours("Jornada de 46 horas a la semana.")
    assert en_digitos is not None and en_digitos.value == 46
    # El span incluye "horas" para que la cita sea verificable por un humano.
    assert "46" in en_digitos.span.text
    assert "hora" in en_digitos.span.text.lower()


# ---------------------------------------------------------------------------
# Nuevos casos: formatos de salario
# ---------------------------------------------------------------------------

def test_salario_con_apostrofo():
    # Separador de miles con apóstrofo: 2'500.000 → igual que 2.500.000.
    text = "Clausula salarial. salario mensual de 2'500.000 m/cte."
    ex = extract_salary(text)
    assert ex is not None
    assert ex.value["amount"] == 2500000
    assert ex.value["periodicity"] == "mensual"
    assert text[ex.span.start:ex.span.end] == ex.span.text


def test_salario_en_palabras_dos_millones_quinientos_mil():
    text = "salario mensual de DOS MILLONES QUINIENTOS MIL PESOS."
    ex = extract_salary(text)
    assert ex is not None
    assert ex.value["amount"] == 2_500_000
    assert ex.value["periodicity"] == "mensual"
    # El span es verificable: apunta a la frase exacta en el texto.
    assert text[ex.span.start:ex.span.end] == ex.span.text
    assert "MILLONES" in ex.span.text


def test_salario_en_palabras_solo_millones():
    text = "salario mensual de UN MILLON de pesos."
    ex = extract_salary(text)
    assert ex is not None
    assert ex.value["amount"] == 1_000_000
    assert text[ex.span.start:ex.span.end] == ex.span.text


def test_salario_en_palabras_span_verificable():
    # El span debe coincidir exactamente con la porción del texto.
    text = "El trabajador devengará un salario mensual de TRES MILLONES QUINIENTOS MIL PESOS."
    ex = extract_salary(text)
    assert ex is not None
    assert ex.value["amount"] == 3_500_000
    assert text[ex.span.start:ex.span.end] == ex.span.text


# ---------------------------------------------------------------------------
# Nuevos casos: fechas en formato dd/mm/aaaa y bordes inválidos
# ---------------------------------------------------------------------------

def test_fecha_inicio_formato_numerico_dd_mm_aaaa():
    text = "El contrato regira a partir del 01/02/2024 y concluye el 31/01/2025."
    inicio = extract_start_date(text)
    assert inicio is not None
    assert inicio.value == "2024-02-01"
    assert text[inicio.span.start:inicio.span.end] == inicio.span.text


def test_fecha_fin_formato_numerico_dd_mm_aaaa():
    text = "El vínculo va desde el 01/02/2024 hasta el 31/01/2025."
    fin = extract_end_date(text)
    assert fin is not None
    assert fin.value == "2025-01-31"
    assert text[fin.span.start:fin.span.end] == fin.span.text


def test_fecha_mes_invalido_devuelve_none():
    # Mes 13 no existe → el extractor no afirma nada.
    text = "Contrato vigente a partir del 01/13/2024."
    assert extract_start_date(text) is None


def test_fecha_dia_cero_devuelve_none():
    # Día 0 no existe → none sin inventar.
    text = "Vigencia a partir del 00/01/2024."
    assert extract_start_date(text) is None


def test_fecha_dia_treintaydos_devuelve_none():
    # Día 32 fuera de rango → none.
    text = "El contrato inicia el 32/01/2024."
    assert extract_start_date(text) is None


# ---------------------------------------------------------------------------
# Nuevos casos: jornada
# ---------------------------------------------------------------------------

def test_jornada_cuarenta_dos_horas_nueva_ley():
    # 42h es el límite de la Ley 2101/2021 — caso crítico para M3 compliance.
    text = "Cumplira una jornada de cuarenta y dos horas semanales conforme a la Ley 2101."
    ex = extract_weekly_hours(text)
    assert ex is not None
    assert ex.value == 42
    assert text[ex.span.start:ex.span.end] == ex.span.text


def test_jornada_sin_keyword_horas_no_extrae():
    # Si no aparece la palabra "horas" no se infiere ninguna jornada.
    text = "La empresa tiene 10 años de experiencia en el mercado."
    assert extract_weekly_hours(text) is None


# ---------------------------------------------------------------------------
# Casos: keyword de salario obligatoria
# ---------------------------------------------------------------------------

def test_salario_sin_keyword_no_extrae():
    # Monto sin la palabra 'salario' cerca → no se asume que es salario.
    text = "El pago asciende a 2.500.000 pesos conforme a lo pactado."
    assert extract_salary(text) is None


def test_salario_quincenal_en_palabras():
    text = "El salario quincenal de DOS MILLONES QUINIENTOS MIL PESOS sera pagado."
    ex = extract_salary(text)
    assert ex is not None
    assert ex.value["amount"] == 2_500_000
    assert ex.value["periodicity"] == "quincenal"
    assert text[ex.span.start:ex.span.end] == ex.span.text


def test_salario_numerico_preferido_si_aparece_primero():
    # Si el monto numérico aparece ANTES que la forma en palabras en la ventana,
    # se usa el numérico (más preciso como span puntual).
    text = "El salario mensual de 3.000.000 pesos (TRES MILLONES) sera pagado."
    ex = extract_salary(text)
    assert ex is not None
    assert ex.value["amount"] == 3_000_000
    # El span debe contener el literal numérico '3.000.000', no la forma en palabras.
    assert "3.000.000" in ex.span.text
    assert "TRES" not in ex.span.text


# ---------------------------------------------------------------------------
# Casos: fechas con separador guión y sin clave contextual
# ---------------------------------------------------------------------------

def test_fecha_guion_separador_dd_mm_aaaa():
    # El regex acepta '-' además de '/' como separador numérico.
    text = "El contrato regira a partir del 01-03-2024 en adelante."
    inicio = extract_start_date(text)
    assert inicio is not None
    assert inicio.value == "2024-03-01"
    assert text[inicio.span.start:inicio.span.end] == inicio.span.text


def test_fecha_sin_clave_contextual_no_extrae():
    # Una fecha en el cuerpo sin keyword de inicio/fin no se extrae.
    text = "La diligencia se celebro el 15 de marzo de 2024 en Cali."
    assert extract_start_date(text) is None
    assert extract_end_date(text) is None


def test_fechas_inicio_y_fin_numericas_en_mismo_texto():
    text = "Vínculo desde el 01/03/2024 hasta el 28/02/2025 en la ciudad."
    inicio = extract_start_date(text)
    fin = extract_end_date(text)
    assert inicio is not None and inicio.value == "2024-03-01"
    assert fin is not None and fin.value == "2025-02-28"
    # Las fechas son distintas y cada una apunta a su tramo correcto.
    assert inicio.value != fin.value
    assert text[inicio.span.start:inicio.span.end] == inicio.span.text
    assert text[fin.span.start:fin.span.end] == fin.span.text


# ---------------------------------------------------------------------------
# Casos: terminacion del vinculo
# ---------------------------------------------------------------------------

def test_terminacion_clausula_explicita_valor_true():
    text = ("El presente contrato se da por terminado de mutuo acuerdo entre las partes "
            "con fecha 31 de enero de 2025.")
    ex = extract_termination(text)
    assert ex is not None
    assert ex.value is True
    assert text[ex.span.start:ex.span.end] == ex.span.text
    assert "terminado" in ex.span.text.lower()


def test_terminacion_por_renuncia_detectada():
    text = "El trabajador presenta renuncia del trabajador con efectos a partir del 15/02/2025."
    ex = extract_termination(text)
    assert ex is not None
    assert ex.value is True


def test_terminacion_acta_detectada():
    text = "Se suscribe la presente acta de terminacion del vinculo laboral."
    ex = extract_termination(text)
    assert ex is not None
    assert ex.value is True
    assert text[ex.span.start:ex.span.end] == ex.span.text


def test_terminacion_ausente_devuelve_none():
    # Contrato a termino fijo vigente sin clausula de terminacion → None.
    text = ("El contrato regira a partir del 1 de febrero de 2024 hasta el 31 de enero "
            "de 2025. Salario mensual: 2.500.000. Jornada: 48 horas semanales.")
    assert extract_termination(text) is None


def test_salario_span_incluye_keyword_min_15():
    text = "El pago salario mensual: 3.500.000 pesos sera efectivo el dia 30."
    ex = extract_salary(text)
    assert ex is not None
    assert len(ex.span.text) >= 15
    assert "3.500.000" in ex.span.text


def test_horas_span_incluye_palabra_horas():
    # El span del digito debe incluir "horas" para que la cita sea legible.
    text = "Trabajara 40 horas semanales segun lo acordado."
    ex = extract_weekly_hours(text)
    assert ex is not None
    assert ex.value == 40
    assert "hora" in ex.span.text.lower()


# ---------------------------------------------------------------------------
# Casos: empleado_nombre y empleado_documento
# ---------------------------------------------------------------------------

def test_empleado_nombre_extrae_del_keyword():
    text = "Trabajador: JUAN PEREZ, C.C. 1.144.000.000. Cargo: Asesor."
    ex = extract_employee_name(text)
    assert ex is not None
    assert ex.value == "JUAN PEREZ"
    assert text[ex.span.start:ex.span.end] == ex.span.text
    assert "Trabajador" in ex.span.text
    assert len(ex.span.text) >= 15


def test_empleado_nombre_multipalabra():
    text = "Trabajadora: MARIA FERNANDA OSPINO GARCIA, identificada con C.C."
    ex = extract_employee_name(text)
    assert ex is not None
    assert "MARIA" in ex.value
    assert "GARCIA" in ex.value


def test_empleado_nombre_ausente_devuelve_none():
    text = "Empleador: Empresa SAS. Cargo: Gerente. Salario: 5.000.000."
    assert extract_employee_name(text) is None


def test_empleado_documento_extrae_cc():
    text = "Trabajador: JUAN PEREZ, C.C. 1.144.000.000. Cargo: Asesor."
    ex = extract_employee_doc(text)
    assert ex is not None
    assert ex.value == "1144000000"
    assert text[ex.span.start:ex.span.end] == ex.span.text
    assert "C.C" in ex.span.text or "C.C." in ex.span.text


def test_empleado_documento_sin_puntos():
    # Cédula sin separadores de miles.
    text = "Identificado con C.C. 12345678 de Cali."
    ex = extract_employee_doc(text)
    assert ex is not None
    assert ex.value == "12345678"


def test_empleado_documento_ausente_devuelve_none():
    text = "El salario mensual es de 2.500.000 pesos."
    assert extract_employee_doc(text) is None


def test_documento_muy_corto_rechazado():
    # Número de menos de 6 dígitos no es una cédula válida.
    text = "Ref. C.C. 123 del empleado."
    assert extract_employee_doc(text) is None


# ---------------------------------------------------------------------------
# Casos: auxilio_transporte
# ---------------------------------------------------------------------------

def test_auxilio_transporte_numerico():
    text = "Salario mensual: 1.750.905. Auxilio de transporte: 249.095 pesos."
    ex = extract_auxilio_transporte(text)
    assert ex is not None
    assert ex.value["amount"] == 249095
    assert ex.value["periodicity"] == "mensual"
    assert text[ex.span.start:ex.span.end] == ex.span.text
    assert "transporte" in ex.span.text.lower()


def test_auxilio_transporte_variante_subsidio():
    text = "Subsidio de transporte: 249.095 m/cte mensuales."
    ex = extract_auxilio_transporte(text)
    assert ex is not None
    assert ex.value["amount"] == 249095


def test_auxilio_transporte_ausente_devuelve_none():
    text = "Salario mensual: 5.000.000 pesos. Jornada: 42 horas semanales."
    assert extract_auxilio_transporte(text) is None


# ---------------------------------------------------------------------------
# Casos: salario_variable
# ---------------------------------------------------------------------------

def test_salario_variable_comisiones():
    text = "El salario se compone de un basico de 1.750.905 mas comisiones por venta."
    ex = extract_salario_variable(text)
    assert ex is not None
    assert ex.value is True
    assert text[ex.span.start:ex.span.end] == ex.span.text
    assert "comision" in ex.span.text.lower()


def test_salario_variable_horas_extras():
    text = "El trabajador devengara su salario mas el pago de horas extras cuando aplique."
    ex = extract_salario_variable(text)
    assert ex is not None
    assert ex.value is True


def test_salario_variable_keyword_explicito():
    text = "La remuneracion sera de salario variable segun metas comerciales."
    ex = extract_salario_variable(text)
    assert ex is not None
    assert ex.value is True


def test_salario_fijo_no_detecta_variable():
    # Contrato de salario fijo: no menciona ningún componente variable.
    # (Un contrato fijo real simplemente no habla de comisiones/HE, no los niega.)
    text = ("El trabajador devengara un salario mensual de 2.500.000 pesos m/cte. "
            "Jornada de 48 horas semanales. Inicio: 1 de febrero de 2024.")
    assert extract_salario_variable(text) is None


# --------------------------------------------------------------------------- #
# Regresión del CASO GOLD (José Ospino): formatos reales que la pipeline E2E
# destapó. El numeral entre paréntesis manda sobre el monto en palabras, y el
# dígito de jornada va entre paréntesis "(48)". Ver scripts/e2e_gold.py.
# --------------------------------------------------------------------------- #

def test_gold_salario_palabras_con_numeral_en_parentesis_prefiere_numeral():
    # Bug E2E: parseaba "UN MILLON" -> 1.000.000 ignorando el numeral exacto.
    text = ("Salario: salario basico mensual de UN MILLON SETECIENTOS CINCUENTA MIL "
            "NOVECIENTOS CINCO PESOS (1.750.905) mas comisiones por ventas.")
    ex = extract_salary(text)
    assert ex is not None
    assert ex.value["amount"] == 1_750_905   # el numeral controlante, no "UN MILLON"
    # La cita debe CERRAR el parentesis del numeral (traza legible para el abogado).
    assert ex.span.text.endswith("(1.750.905)")


def test_gold_jornada_digito_entre_parentesis_48():
    # Bug E2E: "(48) horas" no matcheaba por el ')' entre el dígito y "horas".
    text = "Jornada: cuarenta y ocho (48) horas semanales."
    ex = extract_weekly_hours(text)
    assert ex is not None
    assert ex.value == 48
    # La cita debe incluir el prefijo "Jornada:" (con dos puntos), no solo "(48)".
    assert ex.span.text == "Jornada: cuarenta y ocho (48) horas semanales"


def test_caso2_nombre_tras_contratista_en_prestacion_servicios():
    # Bug E2E caso 2: en prestación de servicios el trabajador es "Contratista:",
    # no "Trabajador:". El extractor debe reconocerlo (caso reclasificación Ley 2466).
    text = "Contratista: ANA SOFIA RESTREPO CARDONA, C.C. 1.144.056.789"
    ex = extract_employee_name(text)
    assert ex is not None
    assert ex.value == "ANA SOFIA RESTREPO CARDONA"


def test_caso2_contratante_no_se_confunde_con_nombre_trabajador():
    # "Contratante" (el empleador) NO debe capturarse como nombre del trabajador.
    text = "Contratante: TECHVALLE SOLUTIONS SAS, NIT 900.765.432-1"
    assert extract_employee_name(text) is None
