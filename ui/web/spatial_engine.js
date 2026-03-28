import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

class SpatialEngine {
    constructor() {
        this.container = document.getElementById('viewport');
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(60, this.container.clientWidth / this.container.clientHeight, 0.1, 1000);
        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        this.controls = null;
        
        this.nodes = new Map();
        this.links = [];
        this.linkMesh = null;
        
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();

        this.init();
    }

    init() {
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.container.appendChild(this.renderer.domElement);

        this.camera.position.set(40, 40, 40);
        this.camera.lookAt(0, 0, 0);
        
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;

        // Lights
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.2);
        this.scene.add(ambientLight);
        
        const mainLight = new THREE.PointLight(0x00e5ff, 2, 100);
        mainLight.position.set(20, 20, 20);
        this.scene.add(mainLight);

        // Futuristic Grid
        const grid = new THREE.GridHelper(200, 40, 0x00e5ff, 0x111111);
        grid.position.y = -30;
        grid.material.opacity = 0.2;
        grid.material.transparent = true;
        this.scene.add(grid);

        // Starfield / Particles
        this.createParticles();

        window.addEventListener('resize', () => this.onResize());
        window.addEventListener('mousedown', (e) => this.onNodeClick(e));
        
        this.animate();
    }

    createParticles() {
        const geometry = new THREE.BufferGeometry();
        const vertices = [];
        for (let i = 0; i < 2000; i++) {
            vertices.push(
                THREE.MathUtils.randFloatSpread(400),
                THREE.MathUtils.randFloatSpread(400),
                THREE.MathUtils.randFloatSpread(400)
            );
        }
        geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
        const material = new THREE.PointsMaterial({ color: 0x888888, size: 0.5, transparent: true, opacity: 0.5 });
        const points = new THREE.Points(geometry, material);
        this.scene.add(points);
    }

    addNode(id, type = 'agent', data = {}) {
        if (this.nodes.has(id)) return;

        const x = (Math.random() - 0.5) * 80;
        const y = (Math.random() - 0.5) * 40;
        const z = (Math.random() - 0.5) * 80;

        let geometry, color;
        switch(type) {
            case 'orchestrator':
                geometry = new THREE.IcosahedronGeometry(2, 1);
                color = 0x9d00ff;
                break;
            case 'mcp':
                geometry = new THREE.BoxGeometry(1.5, 1.5, 1.5);
                color = 0x00ff88;
                break;
            default:
                geometry = new THREE.OctahedronGeometry(1.2, 0);
                color = 0x00e5ff;
        }

        const material = new THREE.MeshStandardMaterial({ 
            color: color,
            emissive: color,
            emissiveIntensity: 0.8,
            metalness: 0.9,
            roughness: 0.1,
            transparent: true,
            opacity: 0.9
        });

        const mesh = new THREE.Mesh(geometry, material);
        mesh.position.set(x, y, z);
        mesh.userData = { id, type, data };
        
        this.scene.add(mesh);
        this.nodes.set(id, mesh);

        // Auto-connect to Kernel/Orchestrator if this isn't the orchestrator
        if (type !== 'orchestrator') {
            for (const [nodeId, nodeMesh] of this.nodes) {
                if (nodeMesh.userData.type === 'orchestrator') {
                    this.connectNodes(id, nodeId);
                }
            }
        }
    }

    connectNodes(id1, id2) {
        const mesh1 = this.nodes.get(id1);
        const mesh2 = this.nodes.get(id2);
        if (!mesh1 || !mesh2) return;

        const points = [mesh1.position, mesh2.position];
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const material = new THREE.LineBasicMaterial({ color: 0x00e5ff, transparent: true, opacity: 0.2 });
        const line = new THREE.Line(geometry, material);
        
        this.scene.add(line);
        this.links.push({ id1, id2, line });
    }

    onNodeClick(event) {
        const rect = this.container.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        this.raycaster.setFromCamera(this.mouse, this.camera);
        const intersects = this.raycaster.intersectObjects(Array.from(this.nodes.values()));

        if (intersects.length > 0) {
            const node = intersects[0].object;
            console.log(`Node interaction: ${node.userData.id}`);
            this.handleNodeInteraction(node);
        }
    }

    handleNodeInteraction(node) {
        // Pulse animation
        const originalScale = node.scale.clone();
        node.scale.set(1.5, 1.5, 1.5);
        setTimeout(() => node.scale.copy(originalScale), 200);

        if (window.appController) {
            window.appController.focusNode(node.userData.id);
        }
    }

    onResize() {
        this.camera.aspect = this.container.clientWidth / this.container.clientHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        this.controls.update();

        // Animate nodes
        const time = Date.now() * 0.001;
        this.nodes.forEach((mesh) => {
            mesh.rotation.y += 0.01;
            mesh.position.y += Math.sin(time + mesh.position.x) * 0.01;
        });

        // Animate links
        this.links.forEach((link) => {
            const p1 = this.nodes.get(link.id1).position;
            const p2 = this.nodes.get(link.id2).position;
            link.line.geometry.setFromPoints([p1, p2]);
            link.line.material.opacity = 0.1 + Math.sin(time * 2) * 0.05;
        });

        this.renderer.render(this.scene, this.camera);
    }
}

export const spatialEngine = new SpatialEngine();
// Sample Kernel node to start
spatialEngine.addNode('kernel-prime', 'orchestrator');
