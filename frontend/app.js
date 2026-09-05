import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

console.log("QUANTUM TRAFFIC SIMULATOR STARTED");

// ======================================================
// SCENE
// ======================================================

const scene = new THREE.Scene();

scene.background = new THREE.Color(0x0b1120);

const camera = new THREE.PerspectiveCamera(
    55,
    window.innerWidth / window.innerHeight,
    0.1,
    1000
);

camera.position.set(24, 22, 24);

// ======================================================
// RENDERER
// ======================================================

const renderer = new THREE.WebGLRenderer({
    antialias: true
});

renderer.setPixelRatio(
    Math.min(window.devicePixelRatio, 2)
);

renderer.shadowMap.enabled = true;

renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const sceneContainer = document.getElementById("scene-container");

const API_URL = "http://127.0.0.1:8001";

const approaches = ["North", "East", "South", "West"];
let trafficSource = "simulation";

let trafficDemand = {
    North: 70,
    East: 30,
    South: 25,
    West: 20
};

let signalTiming = {
    North: 15,
    East: 15,
    South: 15,
    West: 15
};

let optimizedTiming = { ...signalTiming };
let simulationModeLabel = "BEFORE OPTIMIZATION";
let latestBackendResult = null;

let simulationRunning = true;
let simulationStopped = false;

sceneContainer.appendChild(renderer.domElement);

function resizeRenderer() {
    const width = sceneContainer.clientWidth;
    const height = sceneContainer.clientHeight;

    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
}

resizeRenderer();

// ======================================================
// CAMERA
// ======================================================

const controls = new OrbitControls(
    camera,
    renderer.domElement
);

controls.enableDamping = true;

controls.dampingFactor = 0.05;

controls.target.set(
    0,
    0,
    0
);

// ======================================================
// LIGHTING
// ======================================================

const ambientLight =
    new THREE.HemisphereLight(
        0xffffff,
        0x444444,
        2
    );

scene.add(ambientLight);


const sun =
    new THREE.DirectionalLight(
        0xffffff,
        4
    );

sun.position.set(
    20,
    30,
    10
);

sun.castShadow = true;

scene.add(sun);


// ======================================================
// GROUND
// ======================================================

const ground =
    new THREE.Mesh(
        new THREE.PlaneGeometry(
            120,
            120
        ),
        new THREE.MeshStandardMaterial({
            color: 0x263238
        })
    );

ground.rotation.x =
    -Math.PI / 2;

ground.receiveShadow = true;

scene.add(ground);


// ======================================================
// ROADS
// ======================================================

const roadMaterial =
    new THREE.MeshStandardMaterial({
        color: 0x242424
    });


// North-South road

const roadNS =
    new THREE.Mesh(
        new THREE.BoxGeometry(
            12,
            0.12,
            100
        ),
        roadMaterial
    );

roadNS.position.y = 0.06;

roadNS.receiveShadow = true;

scene.add(roadNS);


// East-West road

const roadEW =
    new THREE.Mesh(
        new THREE.BoxGeometry(
            100,
            0.12,
            12
        ),
        roadMaterial
    );

roadEW.position.y = 0.07;

roadEW.receiveShadow = true;

scene.add(roadEW);


// ======================================================
// LANE MARKINGS
// ======================================================

const lineMaterial =
    new THREE.MeshBasicMaterial({
        color: 0xffffff
    });


// Vertical dashed lines

for (
    let z = -45;
    z <= 45;
    z += 6
) {

    if (
        Math.abs(z) < 8
    ) continue;

    const line =
        new THREE.Mesh(
            new THREE.BoxGeometry(
                0.15,
                0.03,
                3
            ),
            lineMaterial
        );

    line.position.set(
        0,
        0.15,
        z
    );

    scene.add(line);
}


// Horizontal dashed lines

for (
    let x = -45;
    x <= 45;
    x += 6
) {

    if (
        Math.abs(x) < 8
    ) continue;

    const line =
        new THREE.Mesh(
            new THREE.BoxGeometry(
                3,
                0.03,
                0.15
            ),
            lineMaterial
        );

    line.position.set(
        x,
        0.16,
        0
    );

    scene.add(line);
}


// ======================================================
// SIDEWALKS
// ======================================================

const sidewalkMaterial =
    new THREE.MeshStandardMaterial({
        color: 0x707070
    });


// Four sidewalk blocks

const sidewalkPositions = [

    [9, 0.15, 9],
    [-9, 0.15, 9],
    [9, 0.15, -9],
    [-9, 0.15, -9]

];

for (
    const pos of sidewalkPositions
) {

    const sidewalk =
        new THREE.Mesh(
            new THREE.BoxGeometry(
                6,
                0.3,
                6
            ),
            sidewalkMaterial
        );

    sidewalk.position.set(
        pos[0],
        pos[1],
        pos[2]
    );

    scene.add(sidewalk);
}


// ======================================================
// TRAFFIC LIGHT CREATION
// ======================================================

// ======================================================
// TRAFFIC LIGHT SYSTEM
// ======================================================

const trafficLights = [];

function createTrafficLight(x, z, rotation, direction) {

    const group = new THREE.Group();

    group.position.set(x, 0, z);
    group.rotation.y = rotation;

    // --------------------------------------------------
    // POLE
    // --------------------------------------------------

    const pole = new THREE.Mesh(
        new THREE.CylinderGeometry(
            0.12,
            0.12,
            5
        ),
        new THREE.MeshStandardMaterial({
            color: 0x111111
        })
    );

    pole.position.y = 2.5;

    pole.castShadow = true;

    group.add(pole);


    // --------------------------------------------------
    // SIGNAL BOX
    // --------------------------------------------------

    const box = new THREE.Mesh(
        new THREE.BoxGeometry(
            0.8,
            2.1,
            0.6
        ),
        new THREE.MeshStandardMaterial({
            color: 0x080808
        })
    );

    box.position.y = 5;

    group.add(box);


    // --------------------------------------------------
    // RED
    // --------------------------------------------------

    const red = new THREE.Mesh(
        new THREE.SphereGeometry(
            0.19,
            20,
            20
        ),
        new THREE.MeshStandardMaterial({
            color: 0x330000,
            emissive: 0x000000
        })
    );

    red.position.set(
        0,
        5.6,
        0.34
    );

    group.add(red);


    // --------------------------------------------------
    // YELLOW
    // --------------------------------------------------

    const yellow = new THREE.Mesh(
        new THREE.SphereGeometry(
            0.19,
            20,
            20
        ),
        new THREE.MeshStandardMaterial({
            color: 0x333300,
            emissive: 0x000000
        })
    );

    yellow.position.set(
        0,
        5.0,
        0.34
    );

    group.add(yellow);


    // --------------------------------------------------
    // GREEN
    // --------------------------------------------------

    const green = new THREE.Mesh(
        new THREE.SphereGeometry(
            0.19,
            20,
            20
        ),
        new THREE.MeshStandardMaterial({
            color: 0x003300,
            emissive: 0x000000
        })
    );

    green.position.set(
        0,
        4.4,
        0.34
    );

    group.add(green);


    // --------------------------------------------------
    // STATUS TEXT
    // --------------------------------------------------

    const canvas =
        document.createElement("canvas");

    canvas.width = 512;
    canvas.height = 128;

    const context =
        canvas.getContext("2d");

    context.fillStyle =
        "rgba(0,0,0,0.85)";

    context.roundRect(
        5,
        5,
        502,
        118,
        20
    );

    context.fill();


    context.font =
        "bold 42px Arial";

    context.textAlign =
        "center";

    context.textBaseline =
        "middle";

    context.fillStyle =
        "#00ff66";

    context.fillText(
        "GO • MOVE",
        256,
        64
    );


    const texture =
        new THREE.CanvasTexture(
            canvas
        );

    texture.needsUpdate = true;


    const material =
        new THREE.SpriteMaterial({
            map: texture,
            transparent: true
        });


    const status =
        new THREE.Sprite(
            material
        );

    status.scale.set(
        4,
        1,
        1
    );

    status.position.set(
        0,
        7,
        0
    );


    group.add(status);


    // --------------------------------------------------
    // SAVE LIGHT DATA
    // --------------------------------------------------

    group.userData.red =
        red;

    group.userData.yellow =
        yellow;

    group.userData.green =
        green;

    group.userData.status =
        status;

    group.userData.canvas =
        canvas;

    group.userData.context =
        context;

    group.userData.direction =
        direction;

    trafficLights.push(
        group
    );

    scene.add(
        group
    );

}


// ======================================================
// UPDATE TRAFFIC LIGHT
// ======================================================

function updateTrafficLight(
    light,
    state
) {

    const red =
        light.userData.red;

    const yellow =
        light.userData.yellow;

    const green =
        light.userData.green;


    // Turn everything OFF

    red.material.emissive.setHex(
        0x000000
    );

    yellow.material.emissive.setHex(
        0x000000
    );

    green.material.emissive.setHex(
        0x000000
    );


    // RED

    if (state === "red") {

        red.material.emissive.setHex(
            0xff0000
        );

        light.userData.context.fillStyle =
            "rgba(0,0,0,0.85)";

        light.userData.context.fillRect(
            0,
            0,
            512,
            128
        );

        light.userData.context.font =
            "bold 42px Arial";

        light.userData.context.textAlign =
            "center";

        light.userData.context.textBaseline =
            "middle";

        light.userData.context.fillStyle =
            "#ff3333";

        light.userData.context.fillText(
            "STOP",
            256,
            64
        );

    }


    // YELLOW

    if (state === "yellow") {

        yellow.material.emissive.setHex(
            0xffff00
        );

        light.userData.context.fillStyle =
            "rgba(0,0,0,0.85)";

        light.userData.context.fillRect(
            0,
            0,
            512,
            128
        );

        light.userData.context.font =
            "bold 42px Arial";

        light.userData.context.textAlign =
            "center";

        light.userData.context.textBaseline =
            "middle";

        light.userData.context.fillStyle =
            "#ffff00";

        light.userData.context.fillText(
            "SLOW DOWN",
            256,
            64
        );

    }


    // GREEN

    if (state === "green") {

        green.material.emissive.setHex(
            0x00ff00
        );

        light.userData.context.fillStyle =
            "rgba(0,0,0,0.85)";

        light.userData.context.fillRect(
            0,
            0,
            512,
            128
        );

        light.userData.context.font =
            "bold 42px Arial";

        light.userData.context.textAlign =
            "center";

        light.userData.context.textBaseline =
            "middle";

        light.userData.context.fillStyle =
            "#00ff66";

        light.userData.context.fillText(
            "GO • MOVE",
            256,
            64
        );

    }


    light.userData.status.material.map.needsUpdate =
        true;

}


// ======================================================
// CREATE FOUR TRAFFIC LIGHTS
// ======================================================

// North
createTrafficLight(
    -5,
    11,
    0,
    "north"
);

// South
createTrafficLight(
    5,
    -11,
    Math.PI,
    "south"
);

// East
createTrafficLight(
    11,
    5,
    Math.PI / 2,
    "east"
);

// West
createTrafficLight(
    -11,
    -5,
    -Math.PI / 2,
    "west"
);


// ======================================================
// TRAFFIC LIGHT CYCLE
// ======================================================

let signalTimer = 0;
let signalPhase = 0;
let lastFrameTime = performance.now();
const signalOrder = ["North", "East", "South", "West"];

function setSignalState(approach, state) {
    trafficLights.forEach(light => {
        if (light.userData.direction === approach.toLowerCase()) {
            updateTrafficLight(light, state);
        }
    });
}

function activeSignalState() {
    const isBeforeOptimization = simulationModeLabel === "BEFORE OPTIMIZATION";
    const activeApproaches = isBeforeOptimization
        ? signalOrder
        : signalOrder.filter(approach => (
            Number(trafficDemand[approach]) > 0 && Number(signalTiming[approach]) > 0
        ));

    if (activeApproaches.length === 0) {
        return { approach: "NONE", state: "red", remaining: 0 };
    }

    const activeApproach = activeApproaches[signalPhase % activeApproaches.length];
    const greenDuration = Number(signalTiming[activeApproach]) || 0;

    if (signalTimer < greenDuration) {
        return { approach: activeApproach, state: "green", remaining: greenDuration - signalTimer };
    }

    return { approach: activeApproach, state: "yellow", remaining: 2 - (signalTimer - greenDuration) };
}

function updateTrafficSignals(deltaSeconds) {
    if (!simulationRunning || simulationStopped) {
        return;
    }

    signalTimer += deltaSeconds;
    const active = activeSignalState();

    signalOrder.forEach(approach => {
        setSignalState(approach, approach === active.approach ? active.state : "red");
    });

    const cycleDuration = (Number(signalTiming[active.approach]) || 0) + 2;
    if (signalTimer >= cycleDuration) {
        signalTimer = 0;
        signalPhase = (signalPhase + 1) % signalOrder.length;
    }

    updateSignalReadout(active);
}

function isApproachOpen(approach) {
    const active = activeSignalState();
    return active.approach === approach && active.state === "green";
}

function updateSignalReadout(active) {
    const directionElement = document.getElementById("currentDirection");
    const countdownElement = document.getElementById("countdown");
    const modeElement = document.getElementById("simulationMode");

    if (directionElement) directionElement.textContent = simulationStopped ? "STOPPED" : active.approach.toUpperCase();
    if (countdownElement) countdownElement.textContent = simulationStopped ? "PAUSED" : `${Math.max(0, active.remaining).toFixed(1)}s`;
    if (modeElement) modeElement.textContent = simulationModeLabel;
}

// ======================================================
// VEHICLES
// ======================================================

const vehicles = [];

let carTemplate = null;


// ======================================================
// LOAD GLB
// ======================================================

const loader =
    new GLTFLoader();

loader.load(

    "./assets/vehicles/car.glb",

    function(gltf) {

        console.log(
            "CAR MODEL LOADED"
        );

        carTemplate =
            gltf.scene;

        normalizeCar(
            carTemplate
        );

        createVehicles();

    },

    undefined,

    function(error) {

        console.error(
            "CAR LOAD ERROR",
            error
        );

    }

);


// ======================================================
// NORMALIZE CAR
// ======================================================

function normalizeCar(
    model
) {

    const box =
        new THREE.Box3()
            .setFromObject(model);

    const size =
        new THREE.Vector3();

    box.getSize(size);

    const largest =
        Math.max(
            size.x,
            size.y,
            size.z
        );

    const scale =
        2.2 / largest;

    model.scale.setScalar(
        scale
    );


    const newBox =
        new THREE.Box3()
            .setFromObject(model);

    const center =
        new THREE.Vector3();

    newBox.getCenter(
        center
    );

    model.position.x -=
        center.x;

    model.position.z -=
        center.z;

    model.position.y -=
        newBox.min.y;

}


// ======================================================
// CREATE VEHICLES
// ======================================================

function createVehicles() {

    vehicles.splice(0).forEach(vehicle => scene.remove(vehicle));

    const positions = [];
    const demandToVehicles = demand => Math.max(0, Math.floor(Number(demand) || 0));

    for (const approach of approaches) {
        const count = demandToVehicles(trafficDemand[approach]);
        const direction = approach.toLowerCase() === "north" ? "south" :
            approach.toLowerCase() === "south" ? "north" :
            approach.toLowerCase() === "east" ? "west" : "east";

        for (let index = 0; index < count; index += 1) {
            const distance = 18 + index * 5;
            positions.push(
                approach === "North" ? { x: -2.5, z: distance, dir: direction, approach } :
                approach === "South" ? { x: 2.5, z: -distance, dir: direction, approach } :
                approach === "East" ? { x: distance, z: 2.5, dir: direction, approach } :
                { x: -distance, z: -2.5, dir: direction, approach }
            );
        }
    }


    for (
        const data of positions
    ) {

        const car =
            carTemplate.clone(
                true
            );

        car.position.set(
            data.x,
            0.2,
            data.z
        );


        // Direction

        if (
            data.dir === "south"
        ) {

            car.rotation.y = Math.PI;

        }

        if (
            data.dir === "north"
        ) {

            car.rotation.y = 0;

        }

        if (
            data.dir === "east"
        ) {

            car.rotation.y =
                Math.PI / 2;

        }

        if (
            data.dir === "west"
        ) {

            car.rotation.y =
                -Math.PI / 2;

        }


        car.userData.direction =
            data.dir;

        car.userData.approach =
            data.approach;

        car.userData.speed =
            3.5 +
            Math.random() * 1.5;


        scene.add(car);

        vehicles.push(
            car
        );

    }

}


// ======================================================
// VEHICLE MOVEMENT
// ======================================================

function updateVehicles() {

    const deltaSeconds = Math.min(0.05, (performance.now() - lastFrameTime) / 1000);
    lastFrameTime = performance.now();
    
    if (simulationStopped) {
        return deltaSeconds;
    }

    for (
        const car of vehicles
    ) {

        const direction =
            car.userData.direction;

        const speed = car.userData.speed * deltaSeconds;
        const stoppedAtRed = !isApproachOpen(car.userData.approach) &&
            isNearStopLine(car);

        if (stoppedAtRed || isFollowingTooClosely(car)) {
            continue;
        }


        if (
            direction === "south"
        ) {

            car.position.z -=
                speed;

            if (
                car.position.z <
                -50
            ) {

                car.position.z =
                    50;

            }

        }


        if (
            direction === "north"
        ) {

            car.position.z +=
                speed;

            if (
                car.position.z >
                50
            ) {

                car.position.z =
                    -50;

            }

        }


        if (
            direction === "east"
        ) {

            car.position.x +=
                speed;

            if (
                car.position.x >
                50
            ) {

                car.position.x =
                    -50;

            }

        }


        if (
            direction === "west"
        ) {

            car.position.x -=
                speed;

            if (
                car.position.x <
                -50
            ) {

                car.position.x =
                    50;

            }

        }

    }

    return deltaSeconds;

}

function isNearStopLine(car) {
    const direction = car.userData.direction;

    if (direction === "south") return car.position.z > 10 && car.position.z < 16;
    if (direction === "north") return car.position.z < -10 && car.position.z > -16;
    if (direction === "west") return car.position.x > 10 && car.position.x < 16;
    return car.position.x < -10 && car.position.x > -16;
}

function isFollowingTooClosely(car) {
    const direction = car.userData.direction;
    const sameLane = other => {
        if (other === car || other.userData.direction !== direction) return false;
        if (direction === "north" || direction === "south") {
            return Math.abs(other.position.x - car.position.x) < 0.5;
        }
        return Math.abs(other.position.z - car.position.z) < 0.5;
    };

    return vehicles.some(other => {
        if (!sameLane(other)) return false;

        if (direction === "south") return other.position.z < car.position.z && car.position.z - other.position.z < 5;
        if (direction === "north") return other.position.z > car.position.z && other.position.z - car.position.z < 5;
        if (direction === "east") return other.position.x > car.position.x && other.position.x - car.position.x < 5;
        return other.position.x < car.position.x && car.position.x - other.position.x < 5;
    });
}

function readDemand() {
    const demand = {};

    approaches.forEach(approach => {
        const input = document.getElementById(approach);
        demand[approach] = Math.max(0, Number(input.value) || 0);
    });

    return demand;
}

function setDemand(demand) {
    trafficDemand = demand;

    approaches.forEach(approach => {
        const input = document.getElementById(approach);
        if (input) input.value = demand[approach];
    });

    if (carTemplate) createVehicles();

    const total = Object.values(demand).reduce((sum, value) => sum + value, 0);
    const status = document.getElementById("demandStatus");
    if (status) status.textContent = `${total} vehicles/cycle configured. Each entered vehicle is shown in the simulation.`;
    setText("totalDemand", total);
}

async function loadAiPrediction() {
    const status = document.getElementById("demandStatus");
    if (status) status.textContent = "Loading AI prediction from the traffic dataset...";

    try {
        const response = await fetch(`${API_URL}/api/predict`);
        if (!response.ok) {
            throw new Error(`Prediction request failed (${response.status})`);
        }

        const result = await response.json();
        setDemand(result.traffic_demand);
        if (status) {
            status.textContent = "AI prediction loaded from traffic.csv. Predicted demand is ready for optimization.";
        }
    } catch (error) {
        if (status) status.textContent = `AI prediction failed: ${error.message}`;
    }
}

function applyTiming(timing, label) {
    signalTiming = { ...timing };
    simulationModeLabel = label;
    signalTimer = 0;
    signalPhase = 0;

    approaches.forEach(approach => {
        const element = document.getElementById(`${approach.toLowerCase()}Timing`);
        if (element) element.textContent = Math.round(signalTiming[approach]);
    });

    const cycleTotal = Object.values(signalTiming).reduce((sum, value) => sum + Number(value), 0);
    document.getElementById("cycleTotal").textContent = `${cycleTotal} sec`;
    document.getElementById("simulationMode").textContent = simulationModeLabel;
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value ?? "—";
}

function formatObjective(value) {
    return typeof value === "number" ? value.toFixed(2) : "—";
}

function formatTiming(value) {
    return value === undefined || value === null ? "—" : `${Math.round(Number(value))}s`;
}

function populateComparisonPage(result) {
    latestBackendResult = result;
    const comparison = result?.comparison || {};
    const strategies = {
        Default: comparison.default,
        Classical: comparison.classical_full,
        Compatible: comparison.classical_quantum_compatible,
        Qaoa: comparison.qaoa
    };

    Object.entries(strategies).forEach(([name, entry]) => {
        const prefix = name === "Default" ? "comparisonDefault" :
            name === "Classical" ? "comparisonClassical" :
            name === "Compatible" ? "comparisonCompatible" : "comparisonQaoa";
        ["North", "East", "South", "West"].forEach(approach => {
            setText(`${prefix}${approach}`, formatTiming(entry?.timing?.[approach]));
        });
        setText(`${prefix}Objective`, formatObjective(entry?.objective));
    });

    const before = comparison.default?.objective;
    const after = comparison.qaoa?.objective;
    const improvement = typeof before === "number" && before !== 0 && typeof after === "number"
        ? `${Math.max(0, ((before - after) / before) * 100).toFixed(2)}%`
        : "—";
    const demand = result?.traffic_demand || trafficDemand;
    const total = Object.values(demand).reduce((sum, value) => sum + Number(value || 0), 0);

    setText("comparisonTotalDemand", total);
    setText("comparisonTrafficObjective", formatObjective(comparison.qaoa?.objective));
    setText("comparisonIbmObjective", formatObjective(result?.qaoa_metadata?.traffic_objective));
    setText("comparisonImprovement", improvement);
    setText("comparisonBackend", result?.qaoa_metadata?.backend);
    setText("comparisonJobId", result?.ibm_job_id || result?.qaoa_metadata?.job_id);
    setText("comparisonQubits", result?.qaoa_metadata?.num_qubits);
    setText("comparisonRuntime", result?.qaoa_metadata?.result_wait_time_seconds === undefined
        ? "—"
        : `${result.qaoa_metadata.result_wait_time_seconds}s`);
    setText("comparisonPageStatus", result?.status === "DONE" ? "RESULT READY" : "WAITING FOR RESULT");
}

function openComparisonPage() {
    const dashboard = document.querySelector(".app > .topbar");
    const comparisonPage = document.getElementById("comparisonPage");
    const dashboardContent = document.querySelector(".app > .dashboard");
    const footer = document.querySelector(".app > .bottom-panel");
    if (!comparisonPage) return;
    comparisonPage.hidden = false;
    if (dashboard) dashboard.hidden = true;
    if (dashboardContent) dashboardContent.hidden = true;
    if (footer) footer.hidden = true;
    if (latestBackendResult) populateComparisonPage(latestBackendResult);
}

function closeComparisonPage() {
    const dashboard = document.querySelector(".app > .topbar");
    const dashboardContent = document.querySelector(".app > .dashboard");
    const footer = document.querySelector(".app > .bottom-panel");
    const comparisonPage = document.getElementById("comparisonPage");
    if (comparisonPage) comparisonPage.hidden = true;
    if (dashboard) dashboard.hidden = false;
    if (dashboardContent) dashboardContent.hidden = false;
    if (footer) footer.hidden = false;
}

async function runOptimization() {

    const button = document.getElementById("runOptimization");
    const status = document.getElementById("demandStatus");

    button.disabled = true;
    button.textContent = "Submitting QAOA...";
    status.textContent = "Preparing traffic demand and submitting job to IBM Quantum...";

    try {

        // ==================================================
        // 1. READ CURRENT TRAFFIC DEMAND
        // ==================================================

        trafficDemand = readDemand();

        // ==================================================
        // 2. SUBMIT IBM QUANTUM JOB
        // ==================================================

        const response = await fetch(
            `${API_URL}/api/optimize`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(trafficDemand)
            }
        );

        if (!response.ok) {

            const errorText = await response.text();

            throw new Error(
                `Backend returned ${response.status}: ${errorText}`
            );
        }

        const submitted = await response.json();

        const jobId = submitted.job_id;

        if (!jobId) {
            throw new Error("Backend did not return an IBM Quantum job ID.");
        }

        console.log("IBM Quantum Job ID:", jobId);

        // ==================================================
        // 3. BACKEND IS ONLINE
        // ==================================================

        document.getElementById("connectionStatus").className =
            "status-dot online";

        setText(
            "connectionText",
            "IBM Quantum Connected"
        );

        setText(
            "qaoaStatus",
            "QUEUED"
        );

        // ==================================================
        // 4. SHOW CLASSICAL INFORMATION IMMEDIATELY
        // ==================================================

        setText(
            "beforeObjective",
            submitted.default_timing
                ? "Running..."
                : "—"
        );

        setText(
            "classicalObjective",
            "Ready"
        );

        setText(
            "classicalCompatibleObjective",
            "Ready"
        );

        setText(
            "qaoaObjective",
            "Waiting..."
        );

        setText(
            "qaoaRuntime",
            "Waiting..."
        );

        setText(
            "qaoaQubits",
            submitted.qaoa_metadata?.num_qubits
                ?? "8"
        );

        setText(
            "qaoaOptimizer",
            "QAOA"
        );

        // ==================================================
        // 5. POLL IBM JOB
        // ==================================================

      // ==================================================
// 5. POLL IBM JOB
// ==================================================

let completedResult = null;

const maxAttempts = 120;

for (
    let attempt = 0;
    attempt < maxAttempts;
    attempt++
) {

    const statusResponse = await fetch(
        `${API_URL}/api/job/${jobId}/status`
    );

    if (!statusResponse.ok) {

        throw new Error(
            `Could not read IBM job status (${statusResponse.status})`
        );
    }

    const statusData =
        await statusResponse.json();

    const jobStatus =
        String(statusData.status || "")
            .toUpperCase();

    console.log(
        `IBM Quantum job status [${attempt + 1}]:`,
        jobStatus
    );

            // ------------------------------------------------
            // UPDATE UI STATUS
            // ------------------------------------------------

            if (
                jobStatus.includes("QUEUED") ||
                jobStatus.includes("INITIALIZING")
            ) {

                setText(
                    "qaoaStatus",
                    "QUEUED"
                );

                status.textContent =
                    "IBM Quantum job is queued. Waiting for hardware execution...";

                button.textContent =
                    "QAOA Queued...";

            }

            else if (
                jobStatus.includes("RUNNING")
            ) {

                setText(
                    "qaoaStatus",
                    "RUNNING"
                );

                status.textContent =
                    "QAOA circuit is running on IBM Quantum hardware...";

                button.textContent =
                    "QAOA Running...";

            }

            else if (
                jobStatus.includes("DONE")
            ) {

                setText(
                    "qaoaStatus",
                    "COMPLETED"
                );

                status.textContent =
                    "IBM Quantum execution completed. Retrieving result...";

                button.textContent =
                    "Retrieving Result...";

                // --------------------------------------------
                // RETRIEVE FINAL RESULT
                // --------------------------------------------

                const resultResponse =
                    await fetch(
                        `${API_URL}/api/job/${jobId}/result`
                    );

                if (!resultResponse.ok) {

                    const errorText =
                        await resultResponse.text();

                    throw new Error(
                        `Could not retrieve QAOA result: ${errorText}`
                    );
                }

                completedResult =
                    await resultResponse.json();

                populateComparisonPage(completedResult);

                break;

            }

            else if (
                jobStatus.includes("ERROR") ||
                jobStatus.includes("CANCEL")
            ) {

                throw new Error(
                    `IBM Quantum job failed with status: ${jobStatus}`
                );
            }

            else {

                setText(
                    "qaoaStatus",
                    jobStatus || "WAITING"
                );

                status.textContent =
                    `IBM Quantum status: ${jobStatus || "WAITING"}...`;

            }

            // ------------------------------------------------
            // WAIT 2 SECONDS BEFORE NEXT CHECK
            // ------------------------------------------------

            await new Promise(
                resolve => setTimeout(resolve, 2000)
            );
        }

        // ==================================================
        // 6. MAKE SURE RESULT WAS RECEIVED
        // ==================================================

        if (!completedResult) {

            throw new Error(
                "IBM Quantum job did not complete within the polling time."
            );
        }

        console.log(
            "FINAL IBM QUANTUM RESULT:",
            completedResult
        );

        // ==================================================
        // 7. GET QAOA TIMING
        // ==================================================

        const timing =
            completedResult.qaoa_timing;

        if (!timing) {

            throw new Error(
                "IBM Quantum result does not contain QAOA timing."
            );
        }

        optimizedTiming = {
            North: Number(timing.North),
            East: Number(timing.East),
            South: Number(timing.South),
            West: Number(timing.West)
        };

        // ==================================================
        // 8. APPLY REAL QAOA TIMING TO 3D SIMULATION
        // ==================================================

        applyTiming(
            optimizedTiming,
            "LIVE IBM QAOA OPTIMIZED"
        );

        // ==================================================
        // 9. UPDATE QAOA RESULT PANEL
        // ==================================================

        setText(
            "qaoaStatus",
            "QAOA READY"
        );

        setText(
            "qaoaObjective",
            completedResult
                .comparison
                ?.qaoa
                ?.objective
                ?.toFixed(2)
        );

        setText(
            "ibmObjective",
            completedResult
                .qaoa_metadata
                ?.traffic_objective
                ?.toFixed(2)
        );

        const runtime =
            completedResult
                .qaoa_metadata
                ?.result_wait_time_seconds;

        setText(
            "qaoaRuntime",
            runtime !== undefined
                ? `${runtime} s`
                : "Completed"
        );

        setText(
            "qaoaQubits",
            completedResult
                .qaoa_metadata
                ?.num_qubits
                ?? "8"
        );

        setText(
            "qaoaOptimizer",
            completedResult
                .qaoa_metadata
                ?.execution
                ?? "IBM Quantum QAOA"
        );

        setText(
            "ibmBackend",
            completedResult
                .qaoa_metadata
                ?.backend
                ?? "—"
        );

        setText(
            "ibmJobId",
            completedResult
                .ibm_job_id
                ?? completedResult.qaoa_metadata?.job_id
                ?? "—"
        );

        // ==================================================
        // 10. UPDATE COMPARISON PANEL
        // ==================================================

        const comparison =
            completedResult.comparison;

        setText(
            "beforeObjective",
            comparison
                ?.default
                ?.objective
                ?.toFixed(2)
        );

        setText(
            "afterObjective",
            comparison
                ?.qaoa
                ?.objective
                ?.toFixed(2)
        );

        setText(
            "classicalObjective",
            comparison
                ?.classical_full
                ?.objective
                ?.toFixed(2)
        );

        setText(
            "classicalCompatibleObjective",
            comparison
                ?.classical_quantum_compatible
                ?.objective
                ?.toFixed(2)
        );

        // ==================================================
        // 11. CALCULATE IMPROVEMENT
        // ==================================================

        const before =
            comparison
                ?.default
                ?.objective;

        const after =
            comparison
                ?.qaoa
                ?.objective;

        if (
            typeof before === "number" &&
            typeof after === "number" &&
            before !== 0
        ) {

            const improvement =
                ((before - after) / before) * 100;

            setText(
                "improvement",
                `${Math.max(0, improvement).toFixed(1)}%`
            );

        }
        else {

            setText(
                "improvement",
                "—"
            );

        }

        // ==================================================
        // 12. REFRESH VEHICLES
        // ==================================================

        setDemand(
            trafficDemand
        );

        // ==================================================
        // 13. FINAL STATUS
        // ==================================================

        status.textContent =
            "✓ IBM Quantum QAOA optimization completed. Optimized signal timing is now controlling the 3D simulation.";

        button.textContent =
            "QAOA Optimization Complete";

        console.log(
            "OPTIMIZED SIGNAL TIMING:",
            optimizedTiming
        );

    }

    catch (error) {

        console.error(
            "QAOA OPTIMIZATION ERROR:",
            error
        );

        status.textContent =
            `Optimization failed: ${error.message}`;

        setText(
            "qaoaStatus",
            "ERROR"
        );

        document.getElementById(
            "connectionStatus"
        ).className =
            "status-dot offline";

        setText(
            "connectionText",
            "Backend Error"
        );

    }

    finally {

        button.disabled = false;

        button.innerHTML =
            "<span>⚛</span> Run QAOA Optimization";

    }
} 

// ======================================================
// ANIMATION
// ======================================================

function animate() {

    requestAnimationFrame(
        animate
    );

    const deltaSeconds = updateVehicles();

    updateTrafficSignals(deltaSeconds);

    controls.update();

    renderer.render(
        scene,
        camera
    );

}

animate();

// ======================================================
// RESIZE
// ======================================================

window.addEventListener("resize", resizeRenderer);


// ======================================================
// SCENARIO DEMANDS
// ======================================================

const scenarioDemand = {
    "morning-rush": {
        North: 100,
        East: 35,
        South: 90,
        West: 25
    },

    "north-south-heavy": {
        North: 120,
        East: 20,
        South: 110,
        West: 20
    },

    "east-heavy": {
        North: 25,
        East: 120,
        South: 25,
        West: 80
    },

    low: {
        North: 10,
        East: 8,
        South: 12,
        West: 6
    },

    balanced: {
        North: 35,
        East: 35,
        South: 35,
        West: 35
    }
};


// ======================================================
// UI INITIALIZATION
// ======================================================

function initializeUI() {

    console.log("=================================");
    console.log("UI INITIALIZATION STARTED");
    console.log("=================================");


    // --------------------------------------------------
    // RUN QAOA BUTTON
    // --------------------------------------------------

    const runButton =
        document.getElementById("runOptimization");

    if (runButton) {

        runButton.addEventListener(
            "click",
            runOptimization
        );

        console.log(
            "✓ Run QAOA button connected"
        );

    } else {

        console.error(
            "✗ Run QAOA button NOT FOUND"
        );
    }

    const comparisonButton =
        document.getElementById("comparisonButton");

    if (comparisonButton) {
        comparisonButton.addEventListener("click", openComparisonPage);
    }

    const comparisonBack =
        document.getElementById("comparisonBack");

    if (comparisonBack) {
        comparisonBack.addEventListener("click", closeComparisonPage);
    }


    // --------------------------------------------------
    // SCENARIO SELECT
    // --------------------------------------------------

    const scenarioSelect =
        document.getElementById("scenarioSelect");

    if (scenarioSelect) {

        scenarioSelect.addEventListener(
            "change",
            event => {

                const selected =
                    event.target.value;

                const isCustom =
                    selected === "custom";


                approaches.forEach(
                    approach => {

                        const input =
                            document.getElementById(
                                approach
                            );

                        if (input) {

                            input.disabled =
                                !isCustom;
                        }
                    }
                );


                if (scenarioDemand[selected]) {

                    setDemand(
                        scenarioDemand[selected]
                    );
                }
            }
        );

        console.log(
            "✓ Scenario selector connected"
        );
    }

    const trafficSourceSelect =
        document.getElementById("trafficSource");

    if (trafficSourceSelect) {
        trafficSourceSelect.addEventListener("change", event => {
            trafficSource = event.target.value;
            const inputs = approaches
                .map(approach => document.getElementById(approach))
                .filter(Boolean);

            if (trafficSource === "ai") {
                inputs.forEach(input => input.disabled = true);
                loadAiPrediction();
            } else if (trafficSource === "custom") {
                inputs.forEach(input => input.disabled = false);
                setText("demandStatus", "Enter custom demand, then run optimization.");
            } else {
                setText("demandStatus", "Choose a traffic scenario, then run optimization.");
            }
        });
    }


    // --------------------------------------------------
    // PLAY / STOP
    // --------------------------------------------------

    const playPause =
        document.getElementById("playPause");

    if (playPause) {

        playPause.addEventListener(
            "click",
            event => {

                simulationStopped =
                    !simulationStopped;

                simulationRunning =
                    !simulationStopped;


                event.currentTarget.textContent =
                    simulationStopped
                        ? "▶ Resume Simulation"
                        : "■ Stop Simulation";


                event.currentTarget.classList.toggle(
                    "stopped",
                    simulationStopped
                );


                updateSignalReadout(
                    activeSignalState()
                );
            }
        );

        console.log(
            "✓ Play/Stop button connected"
        );
    }


    // --------------------------------------------------
    // BEFORE OPTIMIZATION
    // --------------------------------------------------

    const beforeButton =
        document.getElementById("beforeBtn");

    if (beforeButton) {

        beforeButton.addEventListener(
            "click",
            () => {

                applyTiming(
                    {
                        North: 15,
                        East: 15,
                        South: 15,
                        West: 15
                    },
                    "BEFORE OPTIMIZATION"
                );

                console.log(
                    "✓ Before optimization timing applied"
                );
            }
        );

        console.log(
            "✓ Before Optimization button connected"
        );
    }


    // --------------------------------------------------
    // DEMAND INPUTS
    // --------------------------------------------------

    approaches.forEach(
        approach => {

            const input =
                document.getElementById(
                    approach
                );

            if (input) {

                input.addEventListener(
                    "input",
                    () => {

                        setDemand(
                            readDemand()
                        );
                    }
                );
            }
        }
    );


    // --------------------------------------------------
    // INITIAL SIGNAL DISPLAY
    // --------------------------------------------------

    updateSignalReadout(
        activeSignalState()
    );


    console.log(
        "================================="
    );

    console.log(
        "✓ UI INITIALIZATION COMPLETE"
    );

    console.log(
        "================================="
    );
}


// ======================================================
// DOM READY HANDLING
// ======================================================
//
// This works whether app.js is loaded before or
// after DOMContentLoaded.
// ======================================================

if (
    document.readyState === "loading"
) {

    document.addEventListener(
        "DOMContentLoaded",
        initializeUI
    );

} else {

    initializeUI();
}
