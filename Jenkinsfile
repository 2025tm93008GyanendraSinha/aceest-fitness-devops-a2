pipeline {
    agent any

    triggers {
        pollSCM('H/2 * * * *')
    }

    environment {
        DOCKER_REPO = 'gyanendrasinha8301/aceest-fitness'
        SONAR_URL = 'http://localhost:9000'
        SONAR_PROJECT_KEY = 'aceest-fitness-a2'
        K8S_NAMESPACE = 'aceest-fitness'
    }

    stages {
        stage('Checkout & Version Detection') {
            steps {
                checkout scm
                script {
                    env.APP_VERSION = sh(
                        script: '''grep -m1 '^APP_VERSION' ACEest_Fitness.py | cut -d'"' -f4''',
                        returnStdout: true
                    ).trim()
                }
                echo "Detected Application Version: ${env.APP_VERSION} (Build #${env.BUILD_NUMBER})"
            }
        }

        stage('Build Versioned Docker Image') {
            steps {
                sh '''
                    docker build \
                      --build-arg APP_VERSION="$APP_VERSION" \
                      -t "${DOCKER_REPO}:${APP_VERSION}" \
                      -t "${DOCKER_REPO}:${APP_VERSION}-build-${BUILD_NUMBER}" \
                      -t "${DOCKER_REPO}:latest" .
                '''
            }
        }

        stage('In-Container Lint & Pytest Validation') {
            steps {
                sh '''
                    CONTAINER_NAME="aceest-test-${BUILD_NUMBER}"
                    docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
                    mkdir -p reports

                    set +e
                    docker run --name "$CONTAINER_NAME" \
                      "${DOCKER_REPO}:${APP_VERSION}-build-${BUILD_NUMBER}" \
                      sh -c "flake8 ACEest_Fitness.py tests/test_app.py --max-line-length=88 && python -m pytest -v --cov=ACEest_Fitness --cov-report=term-missing --cov-report=xml:/tmp/coverage.xml --junitxml=/tmp/junit.xml tests/"
                    TEST_EXIT=$?
                    set -e

                    docker cp "${CONTAINER_NAME}:/tmp/coverage.xml" reports/coverage.xml || true
                    docker cp "${CONTAINER_NAME}:/tmp/junit.xml" reports/junit.xml || true
                    docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

                    if [ -f reports/coverage.xml ]; then
                        sed -i 's|<source>/app</source>|<source>/usr/src</source>|g' reports/coverage.xml
                    fi

                    exit $TEST_EXIT
                '''
            }
        }

        stage('SonarQube Analysis & Quality Gate') {
            steps {
                withCredentials([string(credentialsId: 'sonarqube-token', variable: 'SONAR_TOKEN')]) {
                    sh '''
                        docker run --rm \
                          --network host \
                          --security-opt label=disable \
                          -e SONAR_HOST_URL="$SONAR_URL" \
                          -e SONAR_TOKEN="$SONAR_TOKEN" \
                          -v "$WORKSPACE:/usr/src:ro" \
                          sonarsource/sonar-scanner-cli \
                          -Dsonar.projectVersion="$APP_VERSION" \
                          -Dsonar.working.directory=/tmp/.scannerwork \
                          -Dsonar.qualitygate.wait=true

                        curl -s -u "$SONAR_TOKEN:" \
                          "${SONAR_URL}/api/qualitygates/project_status?projectKey=${SONAR_PROJECT_KEY}" \
                          | python3 -m json.tool > reports/sonarqube_quality_gate.json

                        curl -s -u "$SONAR_TOKEN:" \
                          "${SONAR_URL}/api/measures/component?component=${SONAR_PROJECT_KEY}&metricKeys=alert_status,bugs,vulnerabilities,code_smells,security_hotspots,coverage,duplicated_lines_density,ncloc,reliability_rating,security_rating,sqale_rating" \
                          | python3 -m json.tool > reports/sonarqube_metrics.json
                    '''
                }
            }
        }

        stage('Package Versioned Build Artifacts') {
            steps {
                sh '''
                    mkdir -p dist
                    ARTIFACT_NAME="dist/aceest-fitness-${APP_VERSION}-build-${BUILD_NUMBER}.tar.gz"
                    tar -czf "$ARTIFACT_NAME" \
                      ACEest_Fitness.py \
                      requirements.txt \
                      Dockerfile \
                      templates/ \
                      k8s/ \
                      reports/
                    ls -lh "$ARTIFACT_NAME"
                '''
                archiveArtifacts artifacts: 'dist/*.tar.gz, reports/*', fingerprint: true
            }
        }

        stage('Push Versioned Images to Docker Hub') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-creds',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh '''
                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
                        docker push "${DOCKER_REPO}:${APP_VERSION}"
                        docker push "${DOCKER_REPO}:${APP_VERSION}-build-${BUILD_NUMBER}"
                        docker push "${DOCKER_REPO}:latest"
                    '''
                }
            }
        }

        stage('Deploy to Kubernetes & Verify Rollout (CD)') {
            steps {
                sh '''
                    kubectl apply -f k8s/00-namespace.yaml
                    kubectl apply -f k8s/03-blue-green.yaml
                    kubectl apply -f k8s/04-canary.yaml
                    kubectl apply -f k8s/05-ab-testing.yaml
                    kubectl apply -f k8s/06-shadow.yaml

                    sed "s|image: ${DOCKER_REPO}:.*|image: ${DOCKER_REPO}:${APP_VERSION}-build-${BUILD_NUMBER}|g" \
                      k8s/02-rolling-update.yaml | kubectl apply -f -

                    if ! kubectl rollout status deployment/aceest-rolling -n "${K8S_NAMESPACE}" --timeout=120s; then
                        echo "Rollout failed! Executing automatic rollback..."
                        kubectl rollout undo deployment/aceest-rolling -n "${K8S_NAMESPACE}"
                        kubectl rollout status deployment/aceest-rolling -n "${K8S_NAMESPACE}" --timeout=120s
                        exit 1
                    fi

                    kubectl get deployments,svc,ingress -n "${K8S_NAMESPACE}"
                '''
            }
        }
    }

    post {
        always {
            sh 'docker logout >/dev/null 2>&1 || true'
        }
        success {
            echo "Full CI/CD Pipeline SUCCEEDED for ACEest Fitness ${env.APP_VERSION} (Build #${env.BUILD_NUMBER})"
        }
        failure {
            echo "CI/CD Pipeline FAILED for ACEest Fitness (Build #${env.BUILD_NUMBER})"
        }
    }
}
