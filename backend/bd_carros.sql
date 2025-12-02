-- ====================================================================
-- SCRIPT FINAL DE INSTALACIÓN: SmartCar Parking System
-- Versión: Definitiva (Incluye Datos Masivos, Auditoría, Alertas, Calendario y Novedades)
-- ====================================================================

-- 1. CONFIGURACIÓN INICIAL DE LA BASE DE DATOS
-- ====================================================================
\c postgres

-- Borrar base de datos si existe
DROP DATABASE IF EXISTS bd_carros;

-- Crear base de datos
CREATE DATABASE bd_carros
WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'es_ES.UTF-8'
    LC_CTYPE = 'es_ES.UTF-8'
    TEMPLATE = template0;

\c bd_carros

-- 2. CREACIÓN DE TABLAS (ESTRUCTURA)
-- ====================================================================

-- Tabla de Status
CREATE TABLE tmstatus (
    cods INTEGER NOT NULL PRIMARY KEY,
    dstatus VARCHAR(12) NOT NULL
);

-- Tabla rol
CREATE TABLE rol (
    id_rol SERIAL PRIMARY KEY,
    nombre_rol VARCHAR(50) NOT NULL UNIQUE
);

-- Tabla persona
CREATE TABLE persona (
    id_persona SERIAL PRIMARY KEY,
    doc_identidad VARCHAR(20) UNIQUE NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    tipo_persona VARCHAR(50) NOT NULL, 
    estado INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (estado) REFERENCES tmstatus(cods) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- Tabla vigilante (Información del personal)
CREATE TABLE vigilante (
    id_vigilante SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    doc_identidad VARCHAR(20) UNIQUE NOT NULL,
    telefono VARCHAR(15),
    estado INTEGER NOT NULL DEFAULT 1,
    id_rol INTEGER,
    FOREIGN KEY (id_rol) REFERENCES rol(id_rol) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (estado) REFERENCES tmstatus(cods) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- Tabla parqueadero
CREATE TABLE parqueadero (
    id_parqueadero SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    capacidad INTEGER NOT NULL,
    ocupados INTEGER NOT NULL DEFAULT 0
);

-- Tabla turno
CREATE TABLE turno (
    id_turno SERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    id_vigilante INTEGER NOT NULL,
    id_parqueadero INTEGER NOT NULL,
    UNIQUE (fecha, id_vigilante),
    FOREIGN KEY (id_vigilante) REFERENCES vigilante(id_vigilante) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (id_parqueadero) REFERENCES parqueadero(id_parqueadero) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- Tabla punto_de_control
CREATE TABLE punto_de_control (
    id_punto SERIAL PRIMARY KEY,
    tipo VARCHAR(50) NOT NULL, 
    id_parqueadero INTEGER NOT NULL,
    FOREIGN KEY (id_parqueadero) REFERENCES parqueadero(id_parqueadero) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- Tabla vehiculo
CREATE TABLE vehiculo (
    id_vehiculo SERIAL PRIMARY KEY,
    placa VARCHAR(10) UNIQUE NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    color VARCHAR(30),
    id_persona INTEGER NOT NULL,
    FOREIGN KEY (id_persona) REFERENCES persona(id_persona) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- Tabla pase_temporal
CREATE TABLE pase_temporal (
    id_pase SERIAL PRIMARY KEY,
    codigo VARCHAR(50) UNIQUE NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    id_persona INTEGER NOT NULL,
    id_vehiculo INTEGER,
    FOREIGN KEY (id_persona) REFERENCES persona(id_persona) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (id_vehiculo) REFERENCES vehiculo(id_vehiculo) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- Tabla identificador
CREATE TABLE identificador (
    id_identificador SERIAL PRIMARY KEY,
    tipo VARCHAR(50) NOT NULL,
    codigo VARCHAR(50) UNIQUE NOT NULL,
    estado INTEGER NOT NULL DEFAULT 1,
    id_vehiculo INTEGER,
    FOREIGN KEY (id_vehiculo) REFERENCES vehiculo(id_vehiculo) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (estado) REFERENCES tmstatus(cods) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- Tabla acceso (CON HORA_SALIDA)
CREATE TABLE acceso (
    id_acceso SERIAL PRIMARY KEY,
    fecha_hora TIMESTAMP NOT NULL DEFAULT NOW(),
    resultado VARCHAR(50) NOT NULL, 
    observaciones TEXT,
    id_vehiculo INTEGER, 
    id_punto INTEGER NOT NULL,
    id_vigilante INTEGER NOT NULL,
    hora_salida TIMESTAMP DEFAULT NULL, -- Nueva columna
    FOREIGN KEY (id_vehiculo) REFERENCES vehiculo(id_vehiculo) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (id_punto) REFERENCES punto_de_control(id_punto) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (id_vigilante) REFERENCES vigilante(id_vigilante) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- Tabla tarifa
CREATE TABLE tarifa (
    id_tarifa SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    condiciones TEXT,
    regla VARCHAR(255),
    valor_base DECIMAL(10, 2) NOT NULL,
    unidad VARCHAR(50) NOT NULL 
);

-- Tabla pago
CREATE TABLE pago (
    id_pago SERIAL PRIMARY KEY,
    fecha_hora TIMESTAMP NOT NULL DEFAULT NOW(),
    importe DECIMAL(10, 2) NOT NULL,
    medio VARCHAR(50),
    ref_transaccion VARCHAR(100) UNIQUE,
    estado INTEGER NOT NULL DEFAULT 1,
    id_acceso_entrada INTEGER,
    id_acceso_salida INTEGER,
    id_tarifa INTEGER NOT NULL,
    id_vigilante INTEGER NOT NULL,
    FOREIGN KEY (id_acceso_entrada) REFERENCES acceso(id_acceso) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (id_acceso_salida) REFERENCES acceso(id_acceso) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (id_tarifa) REFERENCES tarifa(id_tarifa) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (id_vigilante) REFERENCES vigilante(id_vigilante) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (estado) REFERENCES tmstatus(cods) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- Tabla de Usuarios (LOGIN DEL SISTEMA)
CREATE TABLE tmusuarios (
	nu SERIAL NOT NULL PRIMARY KEY,
	nombre VARCHAR(40) NOT NULL,
	usuario VARCHAR(40) NOT NULL UNIQUE,
	clave VARCHAR(40) NOT NULL,
	nivel INTEGER NOT NULL, 
	fkcods INTEGER NOT NULL DEFAULT 1,
	FOREIGN KEY(fkcods) REFERENCES tmstatus(cods)  
			ON UPDATE CASCADE ON DELETE RESTRICT 
);

-- Tabla evento (Módulo Calendario)
CREATE TABLE evento (
    id_evento SERIAL PRIMARY KEY,
    titulo VARCHAR(100) NOT NULL,
    descripcion TEXT,
    fecha_inicio TIMESTAMP NOT NULL,
    fecha_fin TIMESTAMP NOT NULL,
    ubicacion VARCHAR(150),
    categoria VARCHAR(50) NOT NULL,
    verificado BOOLEAN DEFAULT FALSE,
    id_creador INTEGER,
    CONSTRAINT fk_evento_creador FOREIGN KEY(id_creador) REFERENCES tmusuarios(nu) ON DELETE SET NULL
);

-- Tabla alerta
CREATE TABLE alerta (
    id_alerta SERIAL PRIMARY KEY,
    tipo VARCHAR(50) NOT NULL,
    detalle TEXT,
    severidad VARCHAR(50),
    id_acceso INTEGER NOT NULL,
    id_vigilante INTEGER NOT NULL, 
    FOREIGN KEY (id_acceso) REFERENCES acceso(id_acceso) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (id_vigilante) REFERENCES tmusuarios(nu) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- Tabla auditoria
CREATE TABLE auditoria (
    id_auditoria SERIAL PRIMARY KEY,
    fecha_hora TIMESTAMP NOT NULL DEFAULT NOW(),
    entidad VARCHAR(50) NOT NULL,
    id_entidad INTEGER NOT NULL,
    accion VARCHAR(50) NOT NULL,
    id_usuario INTEGER NOT NULL, 
    datos_previos TEXT,
    datos_nuevos TEXT,
    FOREIGN KEY (id_usuario) REFERENCES tmusuarios(nu) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- Tabla NOVEDAD (FALTABA EN TU SCRIPT)
CREATE TABLE novedad (
    id_novedad SERIAL PRIMARY KEY,
    asunto VARCHAR(100) NOT NULL,
    descripcion TEXT NOT NULL,
    fecha_hora TIMESTAMP NOT NULL DEFAULT NOW(),
    id_usuario INTEGER NOT NULL,
    FOREIGN KEY (id_usuario) REFERENCES tmusuarios(nu) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- 3. INSERCIÓN DE DATOS (DATA SEEDING)
-- ====================================================================

-- Status
INSERT INTO tmstatus (cods, dstatus) VALUES (0, 'ELIMINADO'), (1, 'ACTIVO');

-- Roles (Admin y Vigilante)
INSERT INTO rol (id_rol, nombre_rol) VALUES
(1, 'Administrador'),
(2, 'Vigilante');
SELECT pg_catalog.setval('public.rol_id_rol_seq', 2, true);

-- Parqueaderos
INSERT INTO parqueadero (id_parqueadero, nombre, capacidad) VALUES (1, 'Principal', 100), (2, 'Visitantes', 50);
SELECT pg_catalog.setval('public.parqueadero_id_parqueadero_seq', 2, true);

-- Puntos de Control
INSERT INTO punto_de_control (id_punto, tipo, id_parqueadero) VALUES (1, 'Entrada', 1), (2, 'Salida', 1);
SELECT pg_catalog.setval('public.punto_de_control_id_punto_seq', 2, true);

-- Tarifas
INSERT INTO tarifa (id_tarifa, nombre, condiciones, regla, valor_base, unidad) VALUES
(1, 'Visitante por hora', 'Tarifa por cada hora o fracción', 'Costo base por hora', 5.00, 'Hora'),
(2, 'Residente mensual', 'Tarifa fija mensual', 'Costo fijo', 50.00, 'Mes');
SELECT pg_catalog.setval('public.tarifa_id_tarifa_seq', 2, true);

-- USUARIOS DEL SISTEMA (tmusuarios)
INSERT INTO tmusuarios (nu, nombre, usuario, clave, nivel) VALUES
(1, 'ANGIE', 'ADMIN@CARROS.COM', '12345', 1), 
(2, 'LAURA', 'LAURAVIGI@ACCESO.COM', '54321', 0),
(3, 'FERNANDO', 'FERNVIGI@ACCESO.COM', 'fer123', 0),
(4, 'DIEGO', 'VIGILANTE2@ACCESO.COM', 'vigi456',0), 
(5, 'IVALDO', 'IVALDO@ADMIN.COM', 'res001', 1);
SELECT pg_catalog.setval('public.tmusuarios_nu_seq', 5, true);

-- VIGILANTES (Sincronización inicial)
-- Insertamos en 'vigilante' los mismos usuarios que en 'tmusuarios' para que aparezcan en el panel
INSERT INTO vigilante (nombre, doc_identidad, telefono, id_rol, estado)
VALUES
('ANGIE', '1001', '3001234567', 1, 1),
('LAURA', '1002', '3001234568', 2, 1),
('FERNANDO', '1003', '3001234569', 2, 1),
('DIEGO', '1004', '3001234570', 2, 1),
('IVALDO', '1005', '3001234571', 1, 1);
SELECT pg_catalog.setval('public.vigilante_id_vigilante_seq', 5, true);

-- Turnos
INSERT INTO turno (id_turno, fecha, hora_inicio, hora_fin, id_vigilante, id_parqueadero) VALUES
(1, CURRENT_DATE, '07:00:00', '15:00:00', 1, 1);
SELECT pg_catalog.setval('public.turno_id_turno_seq', 1, true);

-- PERSONAS (Datos Masivos + INVITADO 9999)
INSERT INTO persona (id_persona, doc_identidad, nombre, tipo_persona, estado) VALUES
(9999, 'INVITADO', 'INVITADO EVENTO', 'VISITANTE', 1), -- INVITADO GENÉRICO
(3, '1000000003', 'Pedro Gomez', 'ADMINISTRATIVO', 1),
(4, '1000000004', 'Ana Torres', 'ESTUDIANTE', 1),
(6, '1000000006', 'Sofia Castro', 'ESTUDIANTE', 1),
(7, '1000000007', 'Miguel Rios', 'DOCENTE', 1),
(8, '1000000008', 'Elena Vargas', 'DOCENTE', 1),
(9, '1000000009', 'Ricardo Soto', 'ADMINISTRATIVO', 1),
(11, '1000000011', 'Javier Peña', 'ESTUDIANTE', 1),
(12, '1000000012', 'Valeria Luna', 'ESTUDIANTE', 1),
(13, '1000000013', 'Andres Mora', 'DOCENTE', 1),
(14, '1000000014', 'Lucia Gil', 'ADMINISTRATIVO', 1),
(15, '1000000015', 'Daniel Sierra', 'ESTUDIANTE', 1),
(16, '1000000016', 'Marina Vega', 'ESTUDIANTE', 1),
(17, '1000000017', 'Sergio Bravo', 'DOCENTE', 1),
(18, '1000000018', 'Paula Ramos', 'DOCENTE', 1),
(19, '1000000019', 'Felipe Nuñez', 'ESTUDIANTE', 1),
(20, '1000000020', 'Gabriela Diaz', 'ESTUDIANTE', 1),
(21, '1000000021', 'Jorge Guerrero', 'ESTUDIANTE', 1),
(22, '1000000022', 'Natalia Marin', 'DOCENTE', 1),
(23, '1000000023', 'Roberto Cruz', 'ADMINISTRATIVO', 1),
(24, '1000000024', 'Laura Herrera', 'ESTUDIANTE', 1),
(25, '1000000025', 'Diego Vidal', 'ESTUDIANTE', 1),
(26, '1000000026', 'Isabel Flores', 'ESTUDIANTE', 1),
(27, '1000000027', 'Héctor Cárdenas', 'DOCENTE', 1),
(28, '1000000028', 'Marta Navarro', 'ADMINISTRATIVO', 1),
(29, '1000000029', 'Esteban Parra', 'ESTUDIANTE', 1),
(30, '1000000030', 'Victoria Salas', 'ESTUDIANTE', 1),
(31, '1000000031', 'Simón Acosta', 'ESTUDIANTE', 1),
(32, '1000000032', 'Alejandra Pardo', 'DOCENTE', 1),
(33, '1000000033', 'Benjamín Caro', 'ADMINISTRATIVO', 1),
(34, '1000000034', 'Lorena Rico', 'ESTUDIANTE', 1),
(35, '1000000035', 'Gustavo Reyes', 'ESTUDIANTE', 1),
(37, '1000000037', 'David Quintero', 'DOCENTE', 1),
(38, '1000000038', 'Monica Latorre', 'ADMINISTRATIVO', 1),
(39, '1000000039', 'Cristian Blanco', 'ESTUDIANTE', 1),
(40, '1000000040', 'Silvana Morales', 'ESTUDIANTE', 1),
(41, '1000000041', 'Mario Zapata', 'ESTUDIANTE', 1),
(42, '1000000042', 'Liliana Durán', 'DOCENTE', 1),
(43, '1000000043', 'Emilio Rueda', 'ADMINISTRATIVO', 1),
(44, '1000000044', 'Adriana Peña', 'ESTUDIANTE', 1),
(45, '1000000045', 'Carlos Vélez', 'ESTUDIANTE', 1),
(46, '1000000046', 'Diana Echeverri', 'ESTUDIANTE', 1),
(47, '1000000047', 'Oscar Gil', 'DOCENTE', 1),
(48, '1000000048', 'Jimena Hoyos', 'ADMINISTRATIVO', 1),
(49, '1000000049', 'Raúl Torres', 'ESTUDIANTE', 1),
(50, '1000000050', 'Teresa Soto', 'ESTUDIANTE', 1),
(51, '1000000051', 'Víctor Castro', 'ESTUDIANTE', 1),
(52, '1000000052', 'Yolanda Ríos', 'DOCENTE', 1),
(53, '1000000053', 'Juancho', 'ESTUDIANTE', 1),
(1, '1000000001', 'Juan Perez', 'ESTUDIANTE', 1),
(10, '1000000010', 'Camila Ortiz', 'DOCENTE', 1),
(36, '1000000036', 'Andrea Gómez', 'ESTUDIANTE', 0),
(2, '1000000002', 'Maria Lopez', 'ESTUDIANTE', 1),
(54, '1234568998', 'Juan Mantilla', 'ESTUDIANTE', 0),
(55, '1093740947', 'Jose Alejandro Morales Duarte', 'ESTUDIANTE', 1),
(5, '1000000005', 'Pablo Rojas', 'DOCENTE', 1);
SELECT pg_catalog.setval('public.persona_id_persona_seq', 10000, true); 

-- VEHÍCULOS (Datos Masivos)
INSERT INTO vehiculo (id_vehiculo, placa, tipo, color, id_persona) VALUES
(4, 'EFG5H61', 'Automovil', 'Negro', 5),
(5, 'HIJ6K70', 'Motocicleta', 'Blanco', 6),
(6, 'LMN7P89', 'Automovil', 'Azul', 7),
(8, 'UVW9X07', 'Automovil', 'Verde', 9),
(9, 'YZA0B16', 'Motocicleta', 'Amarillo', 10),
(10, 'CDE1F25', 'Automovil', 'Plateado', 11),
(11, 'FGH2I34', 'Automovil', 'Dorado', 12),
(12, 'JKL3M43', 'Motocicleta', 'Gris', 13),
(13, 'NOP4Q52', 'Automovil', 'Negro', 14),
(14, 'RST5U61', 'Camioneta', 'Blanco', 15),
(15, 'VXY6Z70', 'Automovil', 'Azul', 16),
(16, 'ZAB7C89', 'Motocicleta', 'Rojo', 17),
(17, 'CDE8F98', 'Automovil', 'Verde', 18),
(18, 'FGH9I07', 'Automovil', 'Amarillo', 19),
(19, 'JKL0M16', 'Motocicleta', 'Plateado', 20),
(20, 'NOP1Q25', 'Automovil', 'Dorado', 21),
(21, 'RST2U34', 'Camioneta', 'Gris', 22),
(22, 'VXY3Z43', 'Automovil', 'Negro', 23),
(23, 'ZAB4C52', 'Motocicleta', 'Blanco', 24),
(24, 'CDE5F61', 'Automovil', 'Azul', 25),
(25, 'FGH6I70', 'Automovil', 'Rojo', 26),
(26, 'JKL7M89', 'Motocicleta', 'Verde', 27),
(27, 'NOP8Q98', 'Automovil', 'Amarillo', 28),
(28, 'RST9U07', 'Camioneta', 'Plateado', 29),
(29, 'VXY0Z16', 'Automovil', 'Dorado', 30),
(30, 'ZAB1C25', 'Motocicleta', 'Gris', 31),
(31, 'CDE2F34', 'Automovil', 'Negro', 32),
(32, 'FGH3I43', 'Automovil', 'Blanco', 33),
(33, 'JKL4M52', 'Motocicleta', 'Azul', 34),
(34, 'NOP5Q61', 'Automovil', 'Rojo', 35),
(35, 'RST6U70', 'Camioneta', 'Verde', 36),
(36, 'VXY7Z89', 'Automovil', 'Amarillo', 37),
(37, 'ZAB8C98', 'Motocicleta', 'Plateado', 38),
(38, 'CDE9F07', 'Automovil', 'Dorado', 39),
(39, 'FGH0I16', 'Automovil', 'Gris', 40),
(40, 'JKL1M25', 'Motocicleta', 'Negro', 41),
(41, 'NOP2Q34', 'Automovil', 'Blanco', 42),
(42, 'RST3U43', 'Camioneta', 'Azul', 43),
(43, 'VXY4Z52', 'Automovil', 'Rojo', 44),
(44, 'ZAB5C61', 'Motocicleta', 'Verde', 45),
(45, 'CDE6F70', 'Automovil', 'Amarillo', 46),
(46, 'FGH7I89', 'Automovil', 'Plateado', 47),
(47, 'JKL8M98', 'Motocicleta', 'Dorado', 48),
(48, 'NOP9Q07', 'Automovil', 'Gris', 49),
(49, 'RST0U16', 'Camioneta', 'Negro', 50),
(50, 'VXY1Z25', 'Automovil', 'Blanco', 51),
(51, 'ZAB2C34', 'Motocicleta', 'Azul', 52),
(52, 'CDE3F43', 'Automovil', 'Rojo', 53), 
(53, 'XYZ9876', 'Automovil', 'Gris', 1),  
(54, 'DEF123A', 'Motocicleta', 'Negro', 2),
(55, 'GHI456B', 'Automovil', 'Blanco', 3),
(56, 'JKL789C', 'Automovil', 'Azul', 4),
(57, 'MNO012D', 'Camioneta', 'Rojo', 5),
(58, 'PQR345E', 'Automovil', 'Verde', 6),
(59, 'STU678F', 'Motocicleta', 'Amarillo', 7),
(60, 'VWX901G', 'Automovil', 'Plateado', 8),
(61, 'YZA234H', 'Automovil', 'Dorado', 9),
(62, 'BCD567I', 'Motocicleta', 'Gris', 10),
(63, 'EFG890J', 'Automovil', 'Negro', 11),
(64, 'HIJ123K', 'Camioneta', 'Blanco', 12),
(65, 'LMN456L', 'Automovil', 'Azul', 13),
(66, 'OPQ789M', 'Motocicleta', 'Rojo', 14),
(67, 'RST012N', 'Automovil', 'Verde', 15),
(68, 'UVW345O', 'Automovil', 'Amarillo', 16),
(69, 'XYZ678P', 'Motocicleta', 'Plateado', 17),
(70, 'A1B901Q', 'Automovil', 'Dorado', 18),
(71, 'C2D234R', 'Camioneta', 'Gris', 19),
(72, 'E3F567S', 'Automovil', 'Negro', 20),
(73, 'G4H890T', 'Motocicleta', 'Blanco', 21),
(74, 'I5J123U', 'Automovil', 'Azul', 22),
(75, 'K6L456V', 'Automovil', 'Rojo', 23),
(76, 'M7N789W', 'Motocicleta', 'Verde', 24),
(77, 'O8P012X', 'Automovil', 'Amarillo', 25),
(78, 'Q9R345Y', 'Camioneta', 'Plateado', 26),
(79, 'S0T678Z', 'Automovil', 'Dorado', 27),
(80, 'U1V901A', 'Motocicleta', 'Gris', 28),
(81, 'W2X234B', 'Automovil', 'Negro', 29),
(82, 'Y3Z567C', 'Automovil', 'Blanco', 30),
(83, 'A4B890D', 'Motocicleta', 'Azul', 31),
(84, 'C5D123E', 'Automovil', 'Rojo', 32),
(85, 'E6F456F', 'Camioneta', 'Verde', 33),
(86, 'G7H789G', 'Automovil', 'Amarillo', 34),
(87, 'I8J012H', 'Motocicleta', 'Plateado', 35),
(88, 'K9L345I', 'Automovil', 'Dorado', 36),
(89, 'M0N678J', 'Automovil', 'Gris', 37),
(90, 'O1P901K', 'Motocicleta', 'Negro', 38),
(91, 'Q2R234L', 'Automovil', 'Blanco', 39),
(92, 'S3T567M', 'Camioneta', 'Azul', 40),
(93, 'U4V890N', 'Automovil', 'Rojo', 41),
(94, 'W5X123O', 'Motocicleta', 'Verde', 42),
(95, 'Y6Z456P', 'Automovil', 'Amarillo', 43),
(96, 'A7B789Q', 'Automovil', 'Plateado', 44),
(97, 'C8D012R', 'Motocicleta', 'Dorado', 45),
(98, 'E9F345S', 'Automovil', 'Gris', 46),
(99, 'G0H678T', 'Camioneta', 'Negro', 47),
(100, 'I1J901U', 'Automovil', 'Blanco', 48),
(101, 'K2L234V', 'Motocicleta', 'Azul', 49),
(102, 'M3N567W', 'Automovil', 'Rojo', 50),
(104, 'LIU890', 'Automovil', 'Blanco', 50),
(105, 'OMG650', 'Automovil', 'Blanco', 50),
(106, 'YWS85F', 'Motocicleta', 'Rojo', 53),
(107, 'MKI689', 'Automovil', 'Rojo', 53),
(108, 'CVY000', 'Automovil', 'NEGRO', 53),
(1, 'ABC1234', 'Motocicleta', 'Rojo', 1),
(2, 'XYZ5678', 'Automovil', 'Blanco', 2),
(3, 'BTN068', 'Automovil', 'Gris', 4);
SELECT pg_catalog.setval('public.vehiculo_id_vehiculo_seq', 108, true);

-- EVENTOS (Datos de Ejemplo)
INSERT INTO evento (titulo, descripcion, fecha_inicio, fecha_fin, ubicacion, categoria, verificado, id_creador) VALUES 
('Mantenimiento Barrera 1', 'Reparación preventiva.', NOW() + interval '1 day', NOW() + interval '1 day 2 hours', 'Entrada Principal', 'Mantenimiento', false, 1),
('Grado de Ingeniería', 'Reservar zona B.', NOW() + interval '3 days 09:00:00', NOW() + interval '3 days 13:00:00', 'Parqueadero Visitantes', 'Evento Masivo', true, 1);
SELECT pg_catalog.setval('public.evento_id_evento_seq', 2, true);

-- FIN DEL SCRIPT